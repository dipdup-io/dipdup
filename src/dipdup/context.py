import asyncio
import importlib
import logging
import os
import sys
from collections import deque
from contextlib import AsyncExitStack
from contextlib import ExitStack
from contextlib import contextmanager
from contextlib import suppress
from pathlib import Path
from pprint import pformat
from typing import Any
from typing import Awaitable
from typing import Dict
from typing import Iterator
from typing import NoReturn
from typing import Optional
from typing import Set
from typing import Type
from typing import TypeVar
from typing import Union
from typing import cast

from tortoise import Tortoise
from tortoise.exceptions import OperationalError

from dipdup.config import BigMapIndexConfig
from dipdup.config import ContractConfig
from dipdup.config import DipDupConfig
from dipdup.config import EventHookConfig
from dipdup.config import EventIndexConfig
from dipdup.config import HandlerConfig
from dipdup.config import HeadIndexConfig
from dipdup.config import HookConfig
from dipdup.config import OperationIndexConfig
from dipdup.config import PostgresDatabaseConfig
from dipdup.config import ResolvedIndexConfigU
from dipdup.config import TokenTransferIndexConfig
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
from dipdup.exceptions import FrameworkException
from dipdup.exceptions import InitializationRequiredError
from dipdup.exceptions import ReindexingRequiredError
from dipdup.models import Contract
from dipdup.models import ContractMetadata
from dipdup.models import Index
from dipdup.models import ModelUpdate
from dipdup.models import Schema
from dipdup.models import TokenMetadata
from dipdup.prometheus import Metrics
from dipdup.transactions import TransactionManager
from dipdup.utils import FormattedLogger
from dipdup.utils.database import execute_sql
from dipdup.utils.database import execute_sql_query
from dipdup.utils.database import get_connection
from dipdup.utils.database import wipe_schema
from dipdup.utils.sys import is_in_tests

DatasourceT = TypeVar('DatasourceT', bound=Datasource)
pending_indexes: deque[Any] = deque()
pending_hooks: deque[Awaitable[None]] = deque()
rolled_back_indexes: Set[str] = set()


class MetadataCursor:
    _contract = 0
    _token = 0

    def __call__(cls) -> NoReturn:
        raise NotImplementedError('MetadataCursor is a singleton class')

    @classmethod
    async def initialize(cls) -> None:
        """Initialize metadata cursor from the database."""
        if last_contract := await ContractMetadata.filter().order_by('-update_id').first():
            cls._contract = last_contract.update_id
        if last_token := await TokenMetadata.filter().order_by('-update_id').first():
            cls._token = last_token.update_id

    @classmethod
    def contract(cls) -> int:
        """Increment the current contract update ID and return it."""
        cls._contract += 1
        return cls._contract

    @classmethod
    def token(cls) -> int:
        """Increment the current token update ID and return it."""
        cls._token += 1
        return cls._token


class DipDupContext:
    """Common execution context for handler and hook callbacks.

    :param datasources: Mapping of available datasources
    :param config: DipDup configuration
    :param logger: Context-aware logger instance
    """

    def __init__(
        self,
        datasources: Dict[str, Datasource],
        config: DipDupConfig,
        callbacks: 'CallbackManager',
        transactions: TransactionManager,
    ) -> None:
        self.datasources = datasources
        self.config = config
        self._callbacks = callbacks
        self._transactions = transactions
        self.logger = FormattedLogger('dipdup.context')

    def __str__(self) -> str:
        return pformat(self.__dict__)

    async def fire_hook(
        self,
        name: str,
        fmt: Optional[str] = None,
        wait: bool = True,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Fire hook with given name and arguments.

        :param name: Hook name
        :param fmt: Format string for `ctx.logger` messages
        :param wait: Wait for hook to finish or fire and forget
        """
        await self._callbacks.fire_hook(self, name, fmt, wait, *args, **kwargs)

    async def _fire_handler(
        self,
        name: str,
        index: str,
        datasource: TzktDatasource,
        fmt: Optional[str] = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Fire handler with given name and arguments.

        :param name: Handler name
        :param index: Index name
        :param datasource: An instance of datasource that triggered the handler
        :param fmt: Format string for `ctx.logger` messages
        """
        await self._callbacks._fire_handler(self, name, index, datasource, fmt, *args, **kwargs)

    async def execute_sql(self, name: str, *args: Any, **kwargs: Any) -> None:
        """Executes SQL script(s) with given name.

        If the `name` path is a directory, all `.sql` scripts within it will be executed in alphabetical order.

        :param name: File or directory within project's `sql` directory
        """
        await self._callbacks.execute_sql(self, name, *args, **kwargs)

    async def execute_sql_query(self, name: str, *args: Any) -> Any:
        """Executes SQL query with given name

        :param name: SQL query name within `<project>/sql` directory
        """
        return await self._callbacks.execute_sql_query(self, name, *args)

    async def restart(self) -> None:
        """Restart process and continue indexing."""
        os.execl(sys.executable, sys.executable, *sys.argv)

    async def reindex(self, reason: Optional[Union[str, ReindexingReason]] = None, **context: Any) -> None:
        """Drops the entire database and starts the indexing process from scratch.

        :param reason: Reason for reindexing in free-form string
        :param context: Additional information to include in exception message
        """
        if reason is None:
            reason = ReindexingReason.manual
        # NOTE: Do not check for `str`! Enum is inherited from it.
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
            conn = get_connection()
            if isinstance(self.config.database, PostgresDatabaseConfig):
                await wipe_schema(
                    conn=conn,
                    schema_name=self.config.database.schema_name,
                    immune_tables=self.config.database.immune_tables,
                )
            else:
                await Tortoise._drop_databases()
            await self.restart()

        else:
            raise NotImplementedError

    async def add_contract(self, name: str, address: str, typename: Optional[str] = None) -> None:
        """Adds contract to the inventory.

        :param name: Contract name
        :param address: Contract address
        :param typename: Alias for the contract script
        """
        self.logger.info('Creating contract `%s` with typename `%s`', name, typename)
        if contract := self.config.contracts.get(name):
            assert contract.address
            raise ContractAlreadyExistsError(self, name, contract.address)
        if address in self.config._contract_addresses:
            raise ContractAlreadyExistsError(self, name, address)
        else:
            self.config._contract_addresses.add(address)

        contract_config = ContractConfig(
            address=address,
            typename=typename,
        )
        contract_config._name = name
        self.config.contracts[name] = contract_config

        with suppress(OperationalError):
            await Contract(
                name=contract_config.name,
                address=contract_config.address,
                typename=contract_config.typename,
            ).save()

    async def add_index(
        self,
        name: str,
        template: str,
        values: Dict[str, Any],
        first_level: int = 0,
        last_level: int = 0,
        state: Optional[Index] = None,
    ) -> None:
        """Adds a new contract to the inventory.

        :param name: Index name
        :param template: Index template to use
        :param values: Mapping of values to fill template with
        """
        self.config.add_index(name, template, values, first_level, last_level)
        await self._spawn_index(name, state)

    async def _spawn_index(self, name: str, state: Optional[Index] = None) -> None:
        # NOTE: Avoiding circular import
        from dipdup.indexes.big_map.index import BigMapIndex
        from dipdup.indexes.event.index import EventIndex
        from dipdup.indexes.head.index import HeadIndex
        from dipdup.indexes.operation.index import OperationIndex
        from dipdup.indexes.token_transfer.index import TokenTransferIndex

        index_config = cast(ResolvedIndexConfigU, self.config.get_index(name))
        index: OperationIndex | BigMapIndex | HeadIndex | TokenTransferIndex | EventIndex

        datasource_name = index_config.datasource.name
        datasource = self.get_tzkt_datasource(datasource_name)

        if isinstance(index_config, OperationIndexConfig):
            index = OperationIndex(self, index_config, datasource)
        elif isinstance(index_config, BigMapIndexConfig):
            index = BigMapIndex(self, index_config, datasource)
        elif isinstance(index_config, HeadIndexConfig):
            index = HeadIndex(self, index_config, datasource)
        elif isinstance(index_config, TokenTransferIndexConfig):
            index = TokenTransferIndex(self, index_config, datasource)
        elif isinstance(index_config, EventIndexConfig):
            index = EventIndex(self, index_config, datasource)
        else:
            raise NotImplementedError

        await datasource.add_index(index_config)
        for handler_config in index_config.handlers:
            self._callbacks.register_handler(handler_config)
        await index.initialize_state(state)

        # NOTE: IndexDispatcher will handle further initialization when it's time
        pending_indexes.append(index)

    async def update_contract_metadata(
        self,
        network: str,
        address: str,
        metadata: Dict[str, Any],
    ) -> None:
        """
        Inserts or updates corresponding rows in the internal `dipdup_contract_metadata` table
        to provide a generic metadata interface (see docs).

        :param network: Network name (e.g. `mainnet`)
        :param address: Contract address
        :param metadata: Contract metadata to insert/update
        """
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
        """
        Inserts or updates corresponding rows in the internal `dipdup_token_metadata` table
        to provide a generic metadata interface (see docs).

        :param network: Network name (e.g. `mainnet`)
        :param address: Contract address
        :param token_id: Token ID
        :param metadata: Token metadata to insert/update
        """

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
        """Get `tzkt` datasource by name"""
        return self._get_datasource(name, TzktDatasource)

    def get_coinbase_datasource(self, name: str) -> CoinbaseDatasource:
        """Get `coinbase` datasource by name"""
        return self._get_datasource(name, CoinbaseDatasource)

    def get_metadata_datasource(self, name: str) -> MetadataDatasource:
        """Get `metadata` datasource by name"""
        return self._get_datasource(name, MetadataDatasource)

    def get_ipfs_datasource(self, name: str) -> IpfsDatasource:
        """Get `ipfs` datasource by name"""
        return self._get_datasource(name, IpfsDatasource)

    def get_http_datasource(self, name: str) -> HttpDatasource:
        """Get `http` datasource by name"""
        return self._get_datasource(name, HttpDatasource)


class HookContext(DipDupContext):
    """Execution context of hook callbacks.

    :param hook_config: Configuration of current hook
    """

    def __init__(
        self,
        datasources: Dict[str, Datasource],
        config: DipDupConfig,
        callbacks: 'CallbackManager',
        transactions: TransactionManager,
        logger: FormattedLogger,
        hook_config: HookConfig,
    ) -> None:
        super().__init__(datasources, config, callbacks, transactions)
        self.logger = logger
        self.hook_config = hook_config

    @classmethod
    def _wrap(
        cls,
        ctx: DipDupContext,
        logger: FormattedLogger,
        hook_config: HookConfig,
    ) -> 'HookContext':
        return cls(
            datasources=ctx.datasources,
            config=ctx.config,
            callbacks=ctx._callbacks,
            transactions=ctx._transactions,
            logger=logger,
            hook_config=hook_config,
        )

    async def rollback(self, index: str, from_level: int, to_level: int) -> None:
        """Rollback index to a given level reverting all changes made since that level.

        :param index: Index name
        :param from_level: Level to rollback from
        :param to_level: Level to rollback to
        """
        self.logger.info('Rolling back `%s`: %s -> %s', index, from_level, to_level)
        if from_level <= to_level:
            raise FrameworkException(f'Attempt to rollback in future: {from_level} <= {to_level}')
        if from_level - to_level > self.config.advanced.rollback_depth:
            # TODO: Need more context
            await self.reindex(ReindexingReason.rollback)

        models = importlib.import_module(f'{self.config.package}.models')
        async with self._transactions.in_transaction():
            updates = await ModelUpdate.filter(
                level__lte=from_level,
                level__gt=to_level,
                index=index,
            ).order_by('-id')

            if updates:
                self.logger.info(f'Reverting {len(updates)} updates')
            for update in updates:
                model = getattr(models, update.model_name)
                await update.revert(model)

        await Index.filter(name=index).update(level=to_level)
        rolled_back_indexes.add(index)


class TemplateValuesDict(dict[str, Any]):
    """Dictionary with template values."""

    def __init__(self, ctx: Any, **kwargs: Any) -> None:
        self.ctx = ctx
        super().__init__(**kwargs)

    def __getitem__(self, key: str) -> Any:
        try:
            return dict.__getitem__(self, key)
        except KeyError as e:
            raise ConfigurationError(
                f'Index `{self.ctx.index_config.name}` requires `{key}` template value to be set'
            ) from e


class HandlerContext(DipDupContext):
    """Execution context of handler callbacks.

    :param handler_config: Configuration of current handler
    :param datasource: Index datasource instance
    """

    def __init__(
        self,
        datasources: Dict[str, Datasource],
        config: DipDupConfig,
        callbacks: 'CallbackManager',
        transactions: TransactionManager,
        logger: FormattedLogger,
        handler_config: HandlerConfig,
        datasource: TzktDatasource,
    ) -> None:
        super().__init__(datasources, config, callbacks, transactions)
        self.logger = logger
        self.handler_config = handler_config
        self.datasource = datasource
        template_values = handler_config.parent.template_values if handler_config.parent else {}
        self.template_values = TemplateValuesDict(self, **template_values)

    @classmethod
    def _wrap(
        cls,
        ctx: DipDupContext,
        logger: FormattedLogger,
        handler_config: HandlerConfig,
        datasource: TzktDatasource,
    ) -> 'HandlerContext':
        return cls(
            datasources=ctx.datasources,
            config=ctx.config,
            callbacks=ctx._callbacks,
            transactions=ctx._transactions,
            logger=logger,
            handler_config=handler_config,
            datasource=datasource,
        )


class CallbackManager:
    def __init__(self, package: str) -> None:
        self._logger = logging.getLogger('dipdup.callback')
        self._package = package
        self._handlers: Dict[tuple[str, str], HandlerConfig] = {}
        self._hooks: Dict[str, HookConfig] = {}

    async def run(self) -> None:
        self._logger.debug('Starting CallbackManager loop')
        while True:
            while pending_hooks:
                await pending_hooks.popleft()
            await asyncio.sleep(1)

    def register_handler(self, handler_config: HandlerConfig) -> None:
        if not handler_config.parent:
            raise FrameworkException('Handler must have a parent index')

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

    async def _fire_handler(
        self,
        ctx: 'DipDupContext',
        name: str,
        index: str,
        datasource: TzktDatasource,
        fmt: Optional[str] = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        module = f'{self._package}.handlers.{name}'
        handler_config = self._get_handler(name, index)
        new_ctx = HandlerContext._wrap(
            ctx,
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
        *args: Any,
        **kwargs: Any,
    ) -> None:
        module = f'{self._package}.hooks.{name}'
        hook_config = self._get_hook(name)

        if isinstance(hook_config, EventHookConfig):
            if isinstance(ctx, (HandlerContext, HookContext)):
                raise FrameworkException('Event hooks cannot be fired manually')

        new_ctx = HookContext._wrap(
            ctx,
            logger=FormattedLogger(module, fmt),
            hook_config=hook_config,
        )

        self._verify_arguments(new_ctx, *args, **kwargs)

        async def _wrapper() -> None:
            async with AsyncExitStack() as stack:
                stack.enter_context(self._callback_wrapper(module))
                if hook_config.atomic:
                    # NOTE: Do not use versioned transactions here
                    await stack.enter_async_context(new_ctx._transactions.in_transaction())

                await hook_config.callback_fn(new_ctx, *args, **kwargs)

        if wait:
            await _wrapper()
        else:
            pending_hooks.append(_wrapper())

    async def execute_sql(
        self,
        ctx: 'DipDupContext',
        name: str,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Execute SQL script included with the project"""
        # NOTE: Modified `package_path` breaks SQL discovery.
        if is_in_tests():
            return

        sql_path = self._get_sql_path(ctx, name)
        conn = get_connection()
        await execute_sql(conn, sql_path, *args, **kwargs)

    async def execute_sql_query(
        self,
        ctx: 'DipDupContext',
        name: str,
        *values: Any,
    ) -> Any:
        """Execute SQL query included with the project"""
        sql_path = self._get_sql_path(ctx, name)
        conn = get_connection()
        return await execute_sql_query(conn, sql_path, *values)

    @contextmanager
    def _callback_wrapper(self, module: str) -> Iterator[None]:
        with ExitStack() as stack:
            try:
                if Metrics.enabled:
                    stack.enter_context(Metrics.measure_callback_duration(module))
                yield
            # NOTE: Do not wrap known errors like ProjectImportError
            except FrameworkException:
                raise
            except Exception as e:
                raise CallbackError(module, e) from e

    # FIXME: kwargs are ignored, no false alarms though
    @classmethod
    def _verify_arguments(cls, ctx: HookContext, *args: Any, **kwargs: Any) -> None:
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

    def _get_sql_path(self, ctx: 'DipDupContext', name: str) -> Path:
        subpackages = name.split('.')
        sql_path = Path(ctx.config.package_path, 'sql', *subpackages)
        if not sql_path.exists():
            raise InitializationRequiredError(f'Missing SQL directory for hook `{name}`')

        return sql_path
