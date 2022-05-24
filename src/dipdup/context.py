import logging
import os
import sys
from collections import deque
from contextlib import AsyncExitStack
from contextlib import ExitStack
from contextlib import contextmanager
from contextlib import suppress
from os.path import exists
from os.path import join
from pprint import pformat
from typing import Any
from typing import Awaitable
from typing import Deque
from typing import Dict
from typing import Iterator
from typing import Optional
from typing import Tuple
from typing import Type
from typing import TypeVar
from typing import Union
from typing import cast

from tortoise import Tortoise
from tortoise.exceptions import OperationalError
from tortoise.transactions import _get_connection

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
from dipdup.config import TokenTransferIndexConfig
from dipdup.config import TzktDatasourceConfig
from dipdup.datasources.coinbase.datasource import CoinbaseDatasource
from dipdup.datasources.datasource import Datasource
from dipdup.datasources.datasource import HttpDatasource
from dipdup.datasources.ipfs.datasource import IpfsDatasource
from dipdup.datasources.metadata.datasource import MetadataDatasource
from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.enums import ReindexingAction
from dipdup.enums import ReindexingReason
from dipdup.exceptions import CallbackError
from dipdup.exceptions import CallbackTypeError
from dipdup.exceptions import ConfigurationError
from dipdup.exceptions import ContractAlreadyExistsError
from dipdup.exceptions import IndexAlreadyExistsError
from dipdup.exceptions import InitializationRequiredError
from dipdup.exceptions import ReindexingRequiredError
from dipdup.models import Contract
from dipdup.models import ContractMetadata
from dipdup.models import Index
from dipdup.models import Schema
from dipdup.models import TokenMetadata
from dipdup.prometheus import Metrics
from dipdup.utils import FormattedLogger
from dipdup.utils import slowdown
from dipdup.utils.database import execute_sql_scripts
from dipdup.utils.database import in_global_transaction
from dipdup.utils.database import wipe_schema

DatasourceT = TypeVar('DatasourceT', bound=Datasource)
# NOTE: Dependency cycle
pending_indexes = deque()  # type: ignore
pending_hooks: Deque[Awaitable[None]] = deque()


class MetadataCursor:
    _contract = 0
    _token = 0

    def __new__(cls):
        raise NotImplementedError

    @classmethod
    async def initialize(cls) -> None:
        if last_contract := await ContractMetadata.filter().order_by('-update_id').first():
            cls._contract = last_contract.update_id
        if last_token := await TokenMetadata.filter().order_by('-update_id').first():
            cls._token = last_token.update_id

    @classmethod
    def contract(cls) -> int:
        cls._contract += 1
        return cls._contract

    @classmethod
    def token(cls) -> int:
        cls._token += 1
        return cls._token


# TODO: Dataclasses are cool, everyone loves them. Resolve issue with pydantic serialization.
class DipDupContext:
    """Class to store application context

    :param datasources: Mapping of available datasources
    :param config: DipDup configuration
    :param callbacks: Low-level callback interface (intented for internal use)
    :param logger: Context-aware logger instance
    """

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
        wait: bool = True,
        *args,
        **kwargs: Any,
    ) -> None:
        """Fire hook with given name and arguments.

        :param name: Hook name
        :param fmt: Format string for `ctx.logger` messages
        :param wait: Wait for hook to finish or fire and forget
        """
        await self.callbacks.fire_hook(self, name, fmt, wait, *args, **kwargs)

    async def fire_handler(
        self,
        name: str,
        index: str,
        datasource: TzktDatasource,
        fmt: Optional[str] = None,
        *args,
        **kwargs: Any,
    ) -> None:
        """Fire handler with given name and arguments.

        :param name: Handler name
        :param index: Index name
        :param datasource: An instance of datasource that triggered the handler
        :param fmt: Format string for `ctx.logger` messages
        """
        await self.callbacks.fire_handler(self, name, index, datasource, fmt, *args, **kwargs)

    async def execute_sql(self, name: str) -> None:
        """Execute SQL script with given name

        :param name: SQL script name within `<project>/sql` directory
        """
        await self.callbacks.execute_sql(self, name)

    async def restart(self) -> None:
        """Restart indexer preserving CLI arguments"""
        os.execl(sys.executable, sys.executable, *sys.argv)

    async def reindex(self, reason: Optional[Union[str, ReindexingReason]] = None, **context) -> None:
        """Drop the whole database and restart with the same CLI arguments"""
        if reason is None:
            reason = ReindexingReason.manual
        # NOTE: Do not check for `str`!
        elif not isinstance(reason, ReindexingReason):
            context['message'] = reason
            reason = ReindexingReason.manual

        action = self.config.advanced.reindex.get(reason, ReindexingAction.exception)
        self.logger.warning('Reindexing requested: reason `%s`, action `%s`', reason.value, action.value)

        if action == ReindexingAction.ignore:
            # NOTE: Recalculate hashes on the next run
            if reason == ReindexingReason.schema_modified:
                await Schema.filter(name=self.config.schema_name).update(hash='')
            elif reason == ReindexingReason.config_modified:
                await Index.filter().update(config_hash='')
            return

        elif action == ReindexingAction.exception:
            schema = await Schema.filter(name=self.config.schema_name).get()
            if not schema.reindex:
                schema.reindex = reason
                await schema.save()
            raise ReindexingRequiredError(schema.reindex, context)

        elif action == ReindexingAction.wipe:
            conn = _get_connection(None)
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
        # NOTE: Avoiding circular import
        from dipdup.index import BigMapIndex
        from dipdup.index import HeadIndex
        from dipdup.index import OperationIndex
        from dipdup.index import TokenTransferIndex

        index_config = cast(ResolvedIndexConfigT, self.config.get_index(name))
        index: Union[OperationIndex, BigMapIndex, HeadIndex, TokenTransferIndex]

        datasource_name = cast(TzktDatasourceConfig, index_config.datasource).name
        datasource = self.get_tzkt_datasource(datasource_name)

        if isinstance(index_config, OperationIndexConfig):
            index = OperationIndex(self, index_config, datasource)
        elif isinstance(index_config, BigMapIndexConfig):
            index = BigMapIndex(self, index_config, datasource)
        elif isinstance(index_config, HeadIndexConfig):
            index = HeadIndex(self, index_config, datasource)
        elif isinstance(index_config, TokenTransferIndexConfig):
            index = TokenTransferIndex(self, index_config, datasource)
        else:
            raise NotImplementedError

        await datasource.add_index(index_config)
        for handler_config in index_config.handlers:
            self.callbacks.register_handler(handler_config)
        await index.initialize_state(state)

        # NOTE: IndexDispatcher will handle further initialization when it's time
        pending_indexes.append(index)

    async def update_contract_metadata(
        self,
        network: str,
        address: str,
        metadata: Dict[str, Any],
    ) -> None:
        if not self.config.advanced.metadata_interface:
            return
        update_id = MetadataCursor.contract()
        await ContractMetadata.update_or_create(
            network=network,
            contract=address,
            defaults={'metadata': metadata, 'update_id': update_id},
        )

    async def update_token_metadata(
        self,
        network: str,
        address: str,
        token_id: str,
        metadata: Dict[str, Any],
    ) -> None:
        if not self.config.advanced.metadata_interface:
            return
        if not all(str.isdigit(c) for c in token_id):
            raise ValueError('`token_id` must be a number')

        update_id = MetadataCursor.token()
        await TokenMetadata.update_or_create(
            network=network,
            contract=address,
            token_id=token_id,
            defaults={'metadata': metadata, 'update_id': update_id},
        )

    def _get_datasource(self, name: str, type_: Type[DatasourceT]) -> DatasourceT:
        datasource = self.datasources.get(name)
        if not datasource:
            raise ConfigurationError(f'Datasource `{name}` is missing')
        if not isinstance(datasource, type_):
            raise ConfigurationError(f'Datasource `{name}` is not a `{type.__name__}`')
        return datasource

    def get_tzkt_datasource(self, name: str) -> TzktDatasource:
        return self._get_datasource(name, TzktDatasource)

    def get_coinbase_datasource(self, name: str) -> CoinbaseDatasource:
        return self._get_datasource(name, CoinbaseDatasource)

    def get_metadata_datasource(self, name: str) -> MetadataDatasource:
        return self._get_datasource(name, MetadataDatasource)

    def get_ipfs_datasource(self, name: str) -> IpfsDatasource:
        return self._get_datasource(name, IpfsDatasource)

    def get_http_datasource(self, name: str) -> HttpDatasource:
        return self._get_datasource(name, HttpDatasource)


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

    async def run(self) -> None:
        self._logger.debug('Starting CallbackManager loop')
        while True:
            async with slowdown(1):
                while pending_hooks:
                    await pending_hooks.popleft()

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
        module = f'{self._package}.handlers.{name}'
        handler_config = self._get_handler(name, index)
        new_ctx = HandlerContext(
            datasources=ctx.datasources,
            config=ctx.config,
            callbacks=ctx.callbacks,
            logger=FormattedLogger(module, fmt),
            handler_config=handler_config,
            datasource=datasource,
        )
        # NOTE: Handlers are not atomic, levels are. Do not open transaction here.
        with self._callback_wrapper(module):
            await handler_config.callback_fn(new_ctx, *args, **kwargs)

    async def fire_hook(
        self,
        ctx: 'DipDupContext',
        name: str,
        fmt: Optional[str] = None,
        wait: bool = True,
        *args,
        **kwargs: Any,
    ) -> None:
        module = f'{self._package}.hooks.{name}'
        hook_config = self._get_hook(name)
        new_ctx = HookContext(
            datasources=ctx.datasources,
            config=ctx.config,
            callbacks=ctx.callbacks,
            logger=FormattedLogger(module, fmt),
            hook_config=hook_config,
        )

        self._verify_arguments(new_ctx, *args, **kwargs)

        async def _wrapper():
            async with AsyncExitStack() as stack:
                stack.enter_context(self._callback_wrapper(module))
                if hook_config.atomic:
                    await stack.enter_async_context(in_global_transaction())

                await hook_config.callback_fn(ctx, *args, **kwargs)

        if wait:
            await _wrapper()
        else:
            pending_hooks.append(_wrapper())

    async def execute_sql(self, ctx: 'DipDupContext', name: str) -> None:
        """Execute SQL included with project"""
        if not isinstance(ctx.config.database, PostgresDatabaseConfig):
            self._logger.warning('Skipping SQL hook `%s`: not supported on SQLite', name)
            return

        subpackages = name.split('.')
        sql_path = join(ctx.config.package_path, 'sql', *subpackages)
        if not exists(sql_path):
            raise InitializationRequiredError(f'Missing SQL directory for hook `{name}`')

        # NOTE: SQL hooks are executed on default connection
        connection = _get_connection(None)
        await execute_sql_scripts(connection, sql_path)

    @contextmanager
    def _callback_wrapper(self, module: str) -> Iterator[None]:
        try:
            with ExitStack() as stack:
                if Metrics.enabled:
                    stack.enter_context(Metrics.measure_callback_duration(module))
                yield
        except Exception as e:
            if isinstance(e, ReindexingRequiredError):
                raise
            raise CallbackError(module, e) from e

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
