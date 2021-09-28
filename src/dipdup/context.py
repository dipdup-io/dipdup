import logging
import os
import sys
import time
from collections import deque
from contextlib import contextmanager, suppress
from os.path import exists, join
from pprint import pformat
from typing import Any, Dict, Iterator, Optional, Tuple, Union, cast

import sqlparse  # type: ignore
from tortoise import Tortoise
from tortoise.exceptions import OperationalError
from tortoise.transactions import get_connection

from dipdup.config import (
    BigMapIndexConfig,
    ContractConfig,
    DipDupConfig,
    HandlerConfig,
    HookConfig,
    IndexTemplateConfig,
    OperationIndexConfig,
    PostgresDatabaseConfig,
    ResolvedIndexConfigT,
    TzktDatasourceConfig,
)
from dipdup.datasources.datasource import Datasource
from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.exceptions import (
    CallbackError,
    CallbackTypeError,
    ConfigurationError,
    ContractAlreadyExistsError,
    IndexAlreadyExistsError,
    InitializationRequiredError,
    ReindexingRequiredError,
)
from dipdup.models import Contract, ReindexingReason, Schema
from dipdup.utils import FormattedLogger, iter_files
from dipdup.utils.database import create_schema, drop_schema, move_table, truncate_schema

pending_indexes = deque()  # type: ignore
forbid_reindexing = False


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

    async def reindex(self, reason: Optional[Union[str, ReindexingReason]] = None) -> None:
        """Drop all tables or whole database and restart with the same CLI arguments"""
        reason_str = reason.value if isinstance(reason, ReindexingReason) else 'unknown'
        self.logger.warning('Reindexing initialized, reason: %s', reason_str)

        if not reason or isinstance(reason, str):
            reason = ReindexingReason.MANUAL

        if forbid_reindexing:
            schema = await Schema.filter().get()
            if schema.reindex:
                raise ReindexingRequiredError(schema.reindex)

            schema.reindex = reason
            await schema.save()
            raise ReindexingRequiredError(schema.reindex)

        database_config = self.config.database
        if isinstance(database_config, PostgresDatabaseConfig):
            conn = get_connection(None)
            immune_schema_name = f'{database_config.schema_name}_immune'

            if database_config.immune_tables:
                await create_schema(conn, immune_schema_name)
                for table in database_config.immune_tables:
                    await move_table(conn, table, database_config.schema_name, immune_schema_name)

            await truncate_schema(conn, database_config.schema_name)

            if database_config.immune_tables:
                for table in database_config.immune_tables:
                    await move_table(conn, table, immune_schema_name, database_config.schema_name)
                await drop_schema(conn, immune_schema_name)

        else:
            await Tortoise._drop_databases()
        await self.restart()

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

    async def add_index(self, name: str, template: str, values: Dict[str, Any]) -> None:
        self.logger.info('Creating index `%s` from template `%s`', name, template)
        if name in self.config.indexes:
            raise IndexAlreadyExistsError(self, name)

        self.config.indexes[name] = IndexTemplateConfig(
            template=template,
            values=values,
        )
        self.config.initialize()

        await self._spawn_index(name)

    async def _spawn_index(self, name: str) -> None:
        from dipdup.index import BigMapIndex, OperationIndex

        index_config = cast(ResolvedIndexConfigT, self.config.indexes[name])
        index: Union[OperationIndex, BigMapIndex]
        datasource_name = cast(TzktDatasourceConfig, index_config.datasource).name
        datasource = self.datasources[datasource_name]
        if not isinstance(datasource, TzktDatasource):
            raise RuntimeError(f'`{datasource_name}` is not a TzktDatasource')

        if isinstance(index_config, OperationIndexConfig):
            index = OperationIndex(self, index_config, datasource)
        elif isinstance(index_config, BigMapIndexConfig):
            index = BigMapIndex(self, index_config, datasource)
        else:
            raise NotImplementedError

        await datasource.add_index(index_config)
        for handler_config in index_config.handlers:
            self.callbacks.register_handler(handler_config)
        await index.initialize_state()

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
            level = self._logger.info if diff > 1 else self._logger.debug
            level('`%s` %s callback executed in %s seconds', name, kind, diff)
        except Exception as e:
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
