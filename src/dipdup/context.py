import logging
import os
import sys
import time
from collections import deque
from contextlib import contextmanager
from contextlib import suppress
from os.path import exists
from os.path import join
from pprint import pformat
from typing import Any
from typing import Dict
from typing import Iterator
from typing import Optional
from typing import Tuple
from typing import Union
from typing import cast

import sqlparse  # type: ignore
from tortoise import Tortoise
from tortoise.exceptions import OperationalError
from tortoise.transactions import get_connection

from dipdup.config import BigMapIndexConfig
from dipdup.config import ContractConfig
from dipdup.config import DipDupConfig
from dipdup.config import HandlerConfig
from dipdup.config import HeadIndexConfig
from dipdup.config import HookConfig
from dipdup.config import IndexTemplateConfig
from dipdup.config import OperationIndexConfig
from dipdup.config import PostgresDatabaseConfig
from dipdup.config import ResolvedIndexConfigT
from dipdup.config import TzktDatasourceConfig
from dipdup.datasources.datasource import Datasource
from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.enums import ReindexingAction
from dipdup.enums import ReindexingReasonC
from dipdup.enums import reason_to_reasonc
from dipdup.enums import reasonc_to_reason
from dipdup.exceptions import CallbackError
from dipdup.exceptions import CallbackTypeError
from dipdup.exceptions import ConfigurationError
from dipdup.exceptions import ContractAlreadyExistsError
from dipdup.exceptions import IndexAlreadyExistsError
from dipdup.exceptions import InitializationRequiredError
from dipdup.exceptions import ReindexingRequiredError
from dipdup.models import Contract
from dipdup.models import Index
from dipdup.models import ReindexingReason
from dipdup.models import Schema
from dipdup.utils import FormattedLogger
from dipdup.utils import iter_files
from dipdup.utils.database import wipe_schema

pending_indexes = deque()  # type: ignore


# TODO: Dataclasses are cool, everyone loves them. Resolve issue with pydantic serialization.
class DipDupContext:
    def __init__(
        self,
        datasources: Dict[str, Datasource],
        config: DipDupConfig,
        callbacks: 'CallbackManager',
    ) -> None:
        self.datasources = datasources
        self.config = config
        self.callbacks = callbacks
        self.logger = FormattedLogger('dipdup.context')

    def __str__(self) -> str:
        return pformat(self.__dict__)

    async def fire_hook(
        self,
        name: str,
        fmt: Optional[str] = None,
        *args,
        **kwargs: Any,
    ) -> None:
        await self.callbacks.fire_hook(self, name, fmt, *args, **kwargs)

    async def fire_handler(
        self,
        name: str,
        index: str,
        datasource: TzktDatasource,
        fmt: Optional[str] = None,
        *args,
        **kwargs: Any,
    ) -> None:
        await self.callbacks.fire_handler(self, name, index, datasource, fmt, *args, **kwargs)

    async def execute_sql(self, name: str) -> None:
        await self.callbacks.execute_sql(self, name)

    async def restart(self) -> None:
        """Restart preserving CLI arguments"""
        # NOTE: Remove --reindex from arguments to avoid reindexing loop
        if '--reindex' in sys.argv:
            sys.argv.remove('--reindex')
        os.execl(sys.executable, sys.executable, *sys.argv)

    async def reindex(self, reason: Optional[Union[str, ReindexingReason, ReindexingReasonC]] = None, **context) -> None:
        """Drop all tables or whole database and restart with the same CLI arguments"""
        if not reason:
            reason = ReindexingReasonC.manual
        elif isinstance(reason, str):
            context['message'] = reason
            reason = ReindexingReasonC.manual
        elif isinstance(reason, ReindexingReason):
            reason = reason_to_reasonc[reason]
        else:
            raise NotImplementedError

        action = self.config.advanced.reindex.get(reason, ReindexingAction.exception)
        self.logger.warning('Reindexing initialized, reason: %s, action: %s', reason.value, action.value)

        if action == ReindexingAction.ignore:
            if reason == ReindexingReasonC.schema_modified:
                await Schema.filter(name=self.config.schema_name).update(hash='')
            elif reason == ReindexingReasonC.config_modified:
                await Index.filter().update(config_hash='')
            return

        elif action == ReindexingAction.exception:
            schema = await Schema.filter(name=self.config.schema_name).get()
            if not schema.reindex:
                schema.reindex = reasonc_to_reason[reason]
                await schema.save()
            raise ReindexingRequiredError(schema.reindex, context)

        elif action == ReindexingAction.wipe:
            conn = get_connection(None)
            if isinstance(self.config.database, PostgresDatabaseConfig):
                await wipe_schema(conn, self.config.database.schema_name, self.config.database.immune_tables)
            else:
                await Tortoise._drop_databases()
            await self.restart()

        else:
            raise NotImplementedError

    async def add_contract(self, name: str, address: str, typename: Optional[str] = None) -> None:
        self.logger.info('Creating contract `%s` with typename `%s`', name, typename)
        if name in self.config.contracts:
            raise ContractAlreadyExistsError(self, name, address)

        contract_config = ContractConfig(
            address=address,
            typename=typename,
        )
        contract_config.name = name
        self.config.contracts[name] = contract_config

        with suppress(OperationalError):
            await Contract(
                name=contract_config.name,
                address=contract_config.address,
                typename=contract_config.typename,
            ).save()

    # TODO: Option to override first_level/last_level?
    async def add_index(self, name: str, template: str, values: Dict[str, Any], state: Optional[Index] = None) -> None:
        self.logger.info('Creating index `%s` from template `%s`', name, template)
        if name in self.config.indexes:
            raise IndexAlreadyExistsError(self, name)

        self.config.indexes[name] = IndexTemplateConfig(
            template=template,
            values=values,
        )
        self.config.initialize()

        await self.spawn_index(name, state)

    async def spawn_index(self, name: str, state: Optional[Index] = None) -> None:
        from dipdup.index import BigMapIndex
        from dipdup.index import HeadIndex
        from dipdup.index import OperationIndex

        index_config = cast(ResolvedIndexConfigT, self.config.get_index(name))
        index: Union[OperationIndex, BigMapIndex, HeadIndex]

        datasource_name = cast(TzktDatasourceConfig, index_config.datasource).name
        datasource = self.datasources[datasource_name]
        if not isinstance(datasource, TzktDatasource):
            raise RuntimeError(f'`{datasource_name}` is not a TzktDatasource')

        if isinstance(index_config, OperationIndexConfig):
            index = OperationIndex(self, index_config, datasource)
        elif isinstance(index_config, BigMapIndexConfig):
            index = BigMapIndex(self, index_config, datasource)
        elif isinstance(index_config, HeadIndexConfig):
            index = HeadIndex(self, index_config, datasource)
        else:
            raise NotImplementedError

        await datasource.add_index(index_config)
        for handler_config in index_config.handlers:
            self.callbacks.register_handler(handler_config)
        await index.initialize_state(state)

        # NOTE: IndexDispatcher will handle further initialization when it's time
        pending_indexes.append(index)


class HookContext(DipDupContext):
    """Hook callback context."""

    def __init__(
        self,
        datasources: Dict[str, Datasource],
        config: DipDupConfig,
        callbacks: 'CallbackManager',
        logger: FormattedLogger,
        hook_config: HookConfig,
    ) -> None:
        super().__init__(datasources, config, callbacks)
        self.logger = logger
        self.hook_config = hook_config


class TemplateValuesDict(dict):
    def __init__(self, ctx, **kwargs):
        self.ctx = ctx
        super().__init__(**kwargs)

    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError as e:
            raise ConfigurationError(f'Index `{self.ctx.index_config.name}` requires `{key}` template value to be set') from e


class HandlerContext(DipDupContext):
    """Common handler context."""

    def __init__(
        self,
        datasources: Dict[str, Datasource],
        config: DipDupConfig,
        callbacks: 'CallbackManager',
        logger: FormattedLogger,
        handler_config: HandlerConfig,
        datasource: TzktDatasource,
    ) -> None:
        super().__init__(datasources, config, callbacks)
        self.logger = logger
        self.handler_config = handler_config
        self.datasource = datasource
        template_values = handler_config.parent.template_values if handler_config.parent else {}
        self.template_values = TemplateValuesDict(self, **template_values)


class CallbackManager:
    def __init__(self, package: str) -> None:
        self._logger = logging.getLogger('dipdup.callback')
        self._package = package
        self._handlers: Dict[Tuple[str, str], HandlerConfig] = {}
        self._hooks: Dict[str, HookConfig] = {}

    def register_handler(self, handler_config: HandlerConfig) -> None:
        if not handler_config.parent:
            raise RuntimeError('Handler must have a parent index')

        # NOTE: Same handlers can be linked to different indexes, we need to use exact config
        key = (handler_config.callback, handler_config.parent.name)
        if key not in self._handlers:
            self._handlers[key] = handler_config
            handler_config.initialize_callback_fn(self._package)

    def register_hook(self, hook_config: HookConfig) -> None:
        key = hook_config.callback
        if key not in self._hooks:
            self._hooks[key] = hook_config
            hook_config.initialize_callback_fn(self._package)

    async def fire_handler(
        self,
        ctx: 'DipDupContext',
        name: str,
        index: str,
        datasource: TzktDatasource,
        fmt: Optional[str] = None,
        *args,
        **kwargs: Any,
    ) -> None:
        handler_config = self._get_handler(name, index)
        new_ctx = HandlerContext(
            datasources=ctx.datasources,
            config=ctx.config,
            callbacks=ctx.callbacks,
            logger=FormattedLogger(f'dipdup.handlers.{name}', fmt),
            handler_config=handler_config,
            datasource=datasource,
        )
        with self._wrapper('handler', name):
            await handler_config.callback_fn(new_ctx, *args, **kwargs)

    async def fire_hook(
        self,
        ctx: 'DipDupContext',
        name: str,
        fmt: Optional[str] = None,
        *args,
        **kwargs: Any,
    ) -> None:
        hook_config = self._get_hook(name)
        new_ctx = HookContext(
            datasources=ctx.datasources,
            config=ctx.config,
            callbacks=ctx.callbacks,
            logger=FormattedLogger(f'dipdup.hooks.{name}', fmt),
            hook_config=hook_config,
        )

        self._verify_arguments(new_ctx, *args, **kwargs)
        with self._wrapper('hook', name):
            await hook_config.callback_fn(ctx, *args, **kwargs)

    async def execute_sql(self, ctx: 'DipDupContext', name: str) -> None:
        """Execute SQL included with project"""
        if not isinstance(ctx.config.database, PostgresDatabaseConfig):
            self._logger.warning('Skipping SQL hook `%s`: not supported on SQLite', name)
            return

        sql_path = join(ctx.config.package_path, 'sql')
        if not exists(sql_path):
            raise InitializationRequiredError

        paths = (
            # NOTE: `sql` directory -> relative/absolute path
            join(sql_path, name),
            name,
        )

        try:
            path = next(filter(exists, paths))
        except StopIteration:
            # NOTE: Not exactly this type of error
            raise ConfigurationError(f'SQL file/directory `{name}` not exists')

        # NOTE: SQL hooks are executed on default connection
        connection = get_connection(None)

        for file in iter_files(path, '.sql'):
            ctx.logger.info('Executing `%s`', file.name)
            sql = file.read()
            for statement in sqlparse.split(sql):
                # NOTE: Ignore empty statements
                with suppress(AttributeError):
                    await connection.execute_script(statement)

    @contextmanager
    def _wrapper(self, kind: str, name: str) -> Iterator[None]:
        try:
            start = time.perf_counter()
            yield
            diff = time.perf_counter() - start
            level = self._logger.warning if diff > 1 else self._logger.debug
            level('`%s` %s callback executed in %s seconds', name, kind, diff)
        except Exception as e:
            if isinstance(e, ReindexingRequiredError):
                raise
            raise CallbackError(kind, name) from e

    @classmethod
    def _verify_arguments(cls, ctx: HookContext, *args, **kwargs) -> None:
        kwargs_annotations = ctx.hook_config.locate_arguments()
        args_names = tuple(kwargs_annotations.keys())
        args_annotations = tuple(kwargs_annotations.values())

        for i, arg in enumerate(args):
            expected_type = args_annotations[i]
            if expected_type and not isinstance(arg, expected_type):
                raise CallbackTypeError(
                    name=ctx.hook_config.callback,
                    kind='hook',
                    arg=args_names[i],
                    type_=type(arg),
                    expected_type=expected_type,
                )

    def _get_handler(self, name: str, index: str) -> HandlerConfig:
        try:
            return self._handlers[(name, index)]
        except KeyError as e:
            raise ConfigurationError(f'Attempt to fire unregistered handler `{name}` of index `{index}`') from e

    def _get_hook(self, name: str) -> HookConfig:

        try:
            return self._hooks[name]
        except KeyError as e:
            raise ConfigurationError(f'Attempt to fire unregistered hook `{name}`') from e
