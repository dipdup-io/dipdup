from __future__ import annotations

import asyncio
import importlib
import os
import sys
from collections import deque
from contextlib import AsyncExitStack
from contextlib import contextmanager
from contextlib import suppress
from pathlib import Path
from pprint import pformat
from typing import TYPE_CHECKING
from typing import Any
from typing import Literal
from typing import TypeVar
from typing import cast

from tortoise.exceptions import OperationalError

from dipdup import env
from dipdup.config import ContractConfigU
from dipdup.config import DipDupConfig
from dipdup.config import HandlerConfig
from dipdup.config import HookConfig
from dipdup.config import ResolvedIndexConfigU
from dipdup.config.evm import EvmContractConfig
from dipdup.config.evm_subsquid_events import SubsquidEventsIndexConfig
from dipdup.config.tezos import TezosContractConfig
from dipdup.config.tezos_tzkt_big_maps import TzktBigMapsIndexConfig
from dipdup.config.tezos_tzkt_events import TzktEventsIndexConfig
from dipdup.config.tezos_tzkt_head import TzktHeadIndexConfig
from dipdup.config.tezos_tzkt_operations import TzktOperationsIndexConfig
from dipdup.config.tezos_tzkt_operations import TzktOperationsUnfilteredIndexConfig
from dipdup.config.tezos_tzkt_token_balances import TzktTokenBalancesIndexConfig
from dipdup.config.tezos_tzkt_token_transfers import TzktTokenTransfersIndexConfig
from dipdup.database import execute_sql
from dipdup.database import execute_sql_query
from dipdup.database import get_connection
from dipdup.database import wipe_schema
from dipdup.datasources import Datasource
from dipdup.datasources import IndexDatasource
from dipdup.datasources.coinbase import CoinbaseDatasource
from dipdup.datasources.evm_node import EvmNodeDatasource
from dipdup.datasources.evm_subsquid import SubsquidDatasource
from dipdup.datasources.http import HttpDatasource
from dipdup.datasources.ipfs import IpfsDatasource
from dipdup.datasources.tezos_tzkt import TzktDatasource
from dipdup.datasources.tzip_metadata import TzipMetadataDatasource
from dipdup.exceptions import CallbackError
from dipdup.exceptions import ConfigurationError
from dipdup.exceptions import ContractAlreadyExistsError
from dipdup.exceptions import FrameworkException
from dipdup.exceptions import InitializationRequiredError
from dipdup.exceptions import ReindexingRequiredError
from dipdup.models import Contract
from dipdup.models import ContractMetadata
from dipdup.models import Head
from dipdup.models import Index
from dipdup.models import ModelUpdate
from dipdup.models import ReindexingAction
from dipdup.models import ReindexingReason
from dipdup.models import Schema
from dipdup.models import TokenMetadata
from dipdup.performance import _CacheManager
from dipdup.performance import _MetricManager
from dipdup.performance import _QueueManager
from dipdup.performance import caches
from dipdup.performance import metrics
from dipdup.performance import queues
from dipdup.utils import FormattedLogger

if TYPE_CHECKING:
    from collections.abc import Awaitable
    from collections.abc import Iterator
    from types import ModuleType

    from dipdup.config.evm_node import EvmNodeDatasourceConfig
    from dipdup.package import DipDupPackage
    from dipdup.transactions import TransactionManager


DatasourceT = TypeVar('DatasourceT', bound=Datasource[Any])


class MetadataCursor:
    _contract = 0
    _token = 0

    def __init__(self) -> None:
        raise FrameworkException('MetadataCursor is a singleton class')

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

    :param config: DipDup configuration
    :param package: DipDup package
    :param datasources: Mapping of available datasources
    :param transactions: Transaction manager (dev only)
    :param logger: Context-aware logger instance
    """

    def __init__(
        self,
        config: DipDupConfig,
        package: DipDupPackage,
        datasources: dict[str, Datasource[Any]],
        transactions: TransactionManager,
    ) -> None:
        self.config = config
        self.package = package
        self.datasources = datasources
        self.transactions = transactions

        self.logger = FormattedLogger('dipdup.context')
        self._pending_indexes: deque[Any] = deque()
        self._pending_hooks: deque[Awaitable[None]] = deque()
        self._rolled_back_indexes: set[str] = set()
        self._handlers: dict[tuple[str, str], HandlerConfig] = {}
        self._hooks: dict[str, HookConfig] = {}

    def __str__(self) -> str:
        return pformat(self.__dict__)

    # TODO: The next four properties are process-global. Document later.
    @property
    def env(self) -> ModuleType:
        return env

    @property
    def caches(self) -> _CacheManager:
        return caches

    @property
    def metrics(self) -> _MetricManager:
        return metrics

    @property
    def queues(self) -> _QueueManager:
        return queues

    async def restart(self) -> None:
        """Restart process and continue indexing."""
        os.execl(sys.executable, sys.executable, *sys.argv)

    async def reindex(
        self,
        reason: str | ReindexingReason | None = None,
        **context: Any,
    ) -> None:
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

        # NOTE: Reset saved checksums; they will be recalculated on the next run
        if action == ReindexingAction.ignore:
            if reason == ReindexingReason.schema_modified:
                await Schema.filter(name=self.config.schema_name).update(hash=None)
            elif reason == ReindexingReason.config_modified:
                await Index.filter().update(config_hash=None)
            elif reason == ReindexingReason.rollback:
                await Head.filter().update(hash=None)

        elif action == ReindexingAction.exception:
            schema = await Schema.filter(name=self.config.schema_name).get()
            if not schema.reindex:
                schema.reindex = reason
                await schema.save()
            raise ReindexingRequiredError(schema.reindex, context)

        elif action == ReindexingAction.wipe:
            conn = get_connection()
            immune_tables = self.config.database.immune_tables | {'dipdup_meta'}
            await wipe_schema(
                conn=conn,
                schema_name=self.config.database.schema_name,
                immune_tables=immune_tables,
            )
            await self.restart()

        else:
            raise NotImplementedError('Unknown reindexing action', action)

    async def add_contract(
        self,
        kind: Literal['tezos'] | Literal['evm'],
        name: str,
        address: str | None = None,
        typename: str | None = None,
        code_hash: str | int | None = None,
    ) -> None:
        """Adds contract to the inventory.

        :param kind: Either 'tezos' or 'evm' allowed
        :param name: Contract name
        :param address: Contract address
        :param typename: Alias for the contract script
        :param code_hash: Contract code hash
        """
        self.logger.info('Creating %s contract `%s` with typename `%s`', kind, name, typename)

        if name in self.config.contracts:
            raise ContractAlreadyExistsError(name)

        contract_config: ContractConfigU
        if kind == 'tezos':
            contract_config = TezosContractConfig(
                kind=kind,
                address=address,
                code_hash=code_hash,
                typename=typename,
            )
        elif kind == 'evm':
            contract_config = EvmContractConfig(
                kind=kind,
                address=address,
                typename=typename,
            )
        else:
            raise NotImplementedError('Unknown contract kind', kind)

        contract_config._name = name
        self.config.contracts[name] = contract_config

        with suppress(OperationalError):
            await Contract(
                name=contract_config.name,
                address=contract_config.address,
                typename=contract_config.typename,
                code_hash=code_hash,
                kind=kind,
            ).save()

    async def add_index(
        self,
        name: str,
        template: str,
        values: dict[str, Any],
        first_level: int = 0,
        last_level: int = 0,
        state: Index | None = None,
    ) -> None:
        """Adds a new index from template.

        :param name: Index name
        :param template: Index template to use
        :param values: Mapping of values to fill template with
        :param first_level: First level to start indexing from
        :param last_level: Last level to index
        :param state: Initial index state (dev only)
        """
        self.config.add_index(name, template, values, first_level, last_level)
        await self._spawn_index(name, state)

    def _link(self, new_ctx: DipDupContext) -> None:
        new_ctx._pending_indexes = self._pending_indexes
        new_ctx._pending_hooks = self._pending_hooks
        new_ctx._rolled_back_indexes = self._rolled_back_indexes
        new_ctx._handlers = self._handlers
        new_ctx._hooks = self._hooks

    async def _spawn_index(self, name: str, state: Index | None = None) -> Any:
        # NOTE: Avoiding circular import
        from dipdup.indexes.evm_subsquid_events.index import SubsquidEventsIndex
        from dipdup.indexes.tezos_tzkt_big_maps.index import TzktBigMapsIndex
        from dipdup.indexes.tezos_tzkt_events.index import TzktEventsIndex
        from dipdup.indexes.tezos_tzkt_head.index import TzktHeadIndex
        from dipdup.indexes.tezos_tzkt_operations.index import TzktOperationsIndex
        from dipdup.indexes.tezos_tzkt_token_balances.index import TzktTokenBalancesIndex
        from dipdup.indexes.tezos_tzkt_token_transfers.index import TzktTokenTransfersIndex

        index_config = cast(ResolvedIndexConfigU, self.config.get_index(name))
        index: (
            TzktOperationsIndex
            | TzktBigMapsIndex
            | TzktHeadIndex
            | TzktTokenBalancesIndex
            | TzktTokenTransfersIndex
            | TzktEventsIndex
            | SubsquidEventsIndex
        )

        datasource_name = index_config.datasource.name
        datasource: TzktDatasource | SubsquidDatasource
        node_configs: tuple[EvmNodeDatasourceConfig, ...] = ()

        if isinstance(index_config, TzktOperationsIndexConfig | TzktOperationsUnfilteredIndexConfig):
            datasource = self.get_tzkt_datasource(datasource_name)
            index = TzktOperationsIndex(self, index_config, datasource)
        elif isinstance(index_config, TzktBigMapsIndexConfig):
            datasource = self.get_tzkt_datasource(datasource_name)
            index = TzktBigMapsIndex(self, index_config, datasource)
        elif isinstance(index_config, TzktHeadIndexConfig):
            datasource = self.get_tzkt_datasource(datasource_name)
            index = TzktHeadIndex(self, index_config, datasource)
        elif isinstance(index_config, TzktTokenBalancesIndexConfig):
            datasource = self.get_tzkt_datasource(datasource_name)
            index = TzktTokenBalancesIndex(self, index_config, datasource)
        elif isinstance(index_config, TzktTokenTransfersIndexConfig):
            datasource = self.get_tzkt_datasource(datasource_name)
            index = TzktTokenTransfersIndex(self, index_config, datasource)
        elif isinstance(index_config, TzktEventsIndexConfig):
            datasource = self.get_tzkt_datasource(datasource_name)
            index = TzktEventsIndex(self, index_config, datasource)
        elif isinstance(index_config, SubsquidEventsIndexConfig):
            datasource = self.get_subsquid_datasource(datasource_name)
            node_field = index_config.datasource.node
            if node_field:
                node_configs = node_configs + node_field if isinstance(node_field, tuple) else (node_field,)
            index = SubsquidEventsIndex(self, index_config, datasource)
        else:
            raise NotImplementedError

        datasource.add_index(index_config)
        for node_config in node_configs:
            node_datasource = self.get_evm_node_datasource(node_config.name)
            node_datasource.add_index(index_config)

        handlers = (
            (index_config.handler_config,)
            if isinstance(index_config, TzktOperationsUnfilteredIndexConfig | TzktHeadIndexConfig)
            else index_config.handlers
        )
        for handler_config in handlers:
            self.register_handler(handler_config)
        await index.initialize_state(state)

        # NOTE: IndexDispatcher will handle further initialization when it's time
        self._pending_indexes.append(index)
        return index

    # TODO: disable_index(name: str)

    async def update_contract_metadata(
        self,
        network: str,
        address: str,
        metadata: dict[str, Any] | None,
    ) -> None:
        """
        Inserts or updates corresponding rows in the internal `dipdup_contract_metadata` table
        to provide a generic metadata interface (see docs).

        :param network: Network name (e.g. `mainnet`)
        :param address: Contract address
        :param metadata: Contract metadata to insert/update
        """
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
        metadata: dict[str, Any] | None,
    ) -> None:
        """
        Inserts or updates corresponding rows in the internal `dipdup_token_metadata` table
        to provide a generic metadata interface (see docs).

        :param network: Network name (e.g. `mainnet`)
        :param address: Contract address
        :param token_id: Token ID
        :param metadata: Token metadata to insert/update
        """

        if not all(str.isdigit(c) for c in token_id):
            raise ValueError('`token_id` must be a number')

        update_id = MetadataCursor.token()
        await TokenMetadata.update_or_create(
            network=network,
            contract=address,
            token_id=token_id,
            defaults={'metadata': metadata, 'update_id': update_id},
        )

    def _get_datasource(self, name: str, type_: type[DatasourceT]) -> DatasourceT:
        datasource = self.datasources.get(name)
        if not datasource:
            raise ConfigurationError(f'Datasource `{name}` is missing')
        if not isinstance(datasource, type_):
            raise ConfigurationError(f'Datasource `{name}` is not a `{type_.__name__}`')
        return datasource

    def get_tzkt_datasource(self, name: str) -> TzktDatasource:
        """Get `tezos.tzkt` datasource by name"""
        return self._get_datasource(name, TzktDatasource)

    def get_subsquid_datasource(self, name: str) -> SubsquidDatasource:
        """Get `evm.subsquid` datasource by name"""
        return self._get_datasource(name, SubsquidDatasource)

    def get_evm_node_datasource(self, name: str) -> EvmNodeDatasource:
        """Get `evm.node` datasource by name or by linked `evm.subsquid` datasource name"""
        with suppress(ConfigurationError):
            return self._get_datasource(name, EvmNodeDatasource)
        with suppress(ConfigurationError):
            subsquid = self._get_datasource(name, SubsquidDatasource)
            # NOTE: Multiple nodes can be linked to a single subsquid. Network is the same, so grab any.
            random_node = subsquid._config.random_node
            if random_node is None:
                raise ConfigurationError(f'No `evm.node` datasources linked to `{name}`')
            return self._get_datasource(random_node.name, EvmNodeDatasource)
        raise ConfigurationError(f'`{name}` datasource is neither `evm.node` nor `evm.subsquid`')

    def get_coinbase_datasource(self, name: str) -> CoinbaseDatasource:
        """Get `coinbase` datasource by name"""
        return self._get_datasource(name, CoinbaseDatasource)

    def get_metadata_datasource(self, name: str) -> TzipMetadataDatasource:
        """Get `metadata` datasource by name"""
        return self._get_datasource(name, TzipMetadataDatasource)

    def get_ipfs_datasource(self, name: str) -> IpfsDatasource:
        """Get `ipfs` datasource by name"""
        return self._get_datasource(name, IpfsDatasource)

    def get_http_datasource(self, name: str) -> HttpDatasource:
        """Get `http` datasource by name"""
        return self._get_datasource(name, HttpDatasource)

    async def rollback(self, index: str, from_level: int, to_level: int) -> None:
        """Rollback index to a given level reverting all changes made since that level.

        :param index: Index name
        :param from_level: Level to rollback from
        :param to_level: Level to rollback to
        """
        self.logger.info('Rolling back `%s`: %s -> %s', index, from_level, to_level)
        if from_level <= to_level:
            raise FrameworkException(f'Attempt to rollback in future: {from_level} <= {to_level}')

        rollback_depth = self.config.advanced.rollback_depth
        if rollback_depth is None:
            raise FrameworkException('`rollback_depth` is not set')
        if from_level - to_level > rollback_depth:
            await self.reindex(
                ReindexingReason.rollback,
                message='Rollback depth exceeded',
                from_level=from_level,
                to_level=to_level,
                rollback_depth=rollback_depth,
            )

        models = importlib.import_module(f'{self.config.package}.models')
        async with self.transactions.in_transaction():
            updates = await ModelUpdate.filter(
                level__lte=from_level,
                level__gt=to_level,
                index=index,
            ).order_by('-id')

            if updates:
                self.logger.info('Reverting %s updates', len(updates))
            for update in updates:
                model = getattr(models, update.model_name)
                await update.revert(model)

        await Index.filter(name=index).update(level=to_level)
        self._rolled_back_indexes.add(index)

    async def _hooks_loop(self, interval: int) -> None:
        while True:
            while self._pending_hooks:
                await self._pending_hooks.popleft()
            await asyncio.sleep(interval)

    def register_handler(self, handler_config: HandlerConfig) -> None:
        if not handler_config.parent:
            raise FrameworkException('Handler must have a parent index')

        # NOTE: Same handlers can be linked to different indexes, we need to use exact config
        key = (handler_config.callback, handler_config.parent.name)
        if key not in self._handlers:
            self._handlers[key] = handler_config

    def register_hook(self, hook_config: HookConfig) -> None:
        key = hook_config.callback
        if key not in self._hooks:
            self._hooks[key] = hook_config

    async def fire_handler(
        self,
        name: str,
        index: str,
        datasource: IndexDatasource[Any],
        fmt: str | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Fire handler with given name and arguments.

        :param name: Handler name
        :param index: Index name
        :param datasource: An instance of datasource that triggered the handler
        :param fmt: Format string for `ctx.logger` messages
        """
        module = f'{self.package.name}.handlers.{name}'
        handler_config = self._get_handler(name, index)
        new_ctx = HandlerContext._wrap(
            self,
            logger=FormattedLogger(module, fmt),
            handler_config=handler_config,
            datasource=datasource,
        )
        # NOTE: Handlers are not atomic, levels are. Do not open transaction here.
        with self._callback_wrapper(module):
            fn = self.package.get_callback('handlers', name, name.split('.')[-1])
            await fn(new_ctx, *args, **kwargs)

    async def fire_hook(
        self,
        name: str,
        fmt: str | None = None,
        wait: bool = True,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Fire hook with given name and arguments.

        :param name: Hook name
        :param fmt: Format string for `ctx.logger` messages
        :param wait: Wait for hook to finish or fire and forget
        :param args: Positional arguments to pass to the hook
        :param kwargs: Keyword arguments to pass to the hook
        """
        module = f'{self.package.name}.hooks.{name}'
        hook_config = self._get_hook(name)

        new_ctx = HookContext._wrap(
            self,
            logger=FormattedLogger(module, fmt),
            hook_config=hook_config,
        )

        async def _wrapper() -> None:
            async with AsyncExitStack() as stack:
                stack.enter_context(self._callback_wrapper(module))
                if hook_config.atomic:
                    # NOTE: Do not use versioned transactions here
                    await stack.enter_async_context(new_ctx.transactions.in_transaction())

                fn = self.package.get_callback('hooks', name, name)
                await fn(new_ctx, *args, **kwargs)

        coro = _wrapper()
        await coro if wait else self._pending_hooks.append(coro)

    async def execute_sql(
        self,
        name: str,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Executes SQL script(s) with given name.

        If the `name` path is a directory, all `.sql` scripts within it will be executed in alphabetical order.

        :param name: File or directory within project's `sql` directory
        :param args: Positional arguments to pass to the script
        :param kwargs: Keyword arguments to pass to the script
        """
        # NOTE: Modified `package_path` breaks SQL discovery.
        if env.TEST:
            return

        sql_path = self._get_sql_path(name)
        conn = get_connection()
        await execute_sql(conn, sql_path, *args, **kwargs)

    async def execute_sql_query(
        self,
        name: str,
        *values: Any,
    ) -> Any:
        """Executes SQL query with given name included with the project

        :param name: SQL query name within `sql` directory
        :param values: Values to pass to the query
        """

        sql_path = self._get_sql_path(name)
        conn = get_connection()
        return await execute_sql_query(conn, sql_path, *values)

    @contextmanager
    def _callback_wrapper(self, module: str) -> Iterator[None]:
        try:
            yield
        # NOTE: Do not wrap known errors like ProjectImportError
        except FrameworkException:
            raise
        except Exception as e:
            raise CallbackError(module, e) from e

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

    def _get_sql_path(self, name: str) -> Path:
        subpackages = name.split('.')
        sql_path = Path(env.get_package_path(self.config.package), 'sql', *subpackages)
        if not sql_path.exists():
            raise InitializationRequiredError(f'Missing SQL directory for hook `{name}`')

        return sql_path


class HookContext(DipDupContext):
    """Execution context of hook callbacks.

    :param hook_config: Configuration of the current hook
    """

    def __init__(
        self,
        config: DipDupConfig,
        package: DipDupPackage,
        datasources: dict[str, Datasource[Any]],
        transactions: TransactionManager,
        logger: FormattedLogger,
        hook_config: HookConfig,
    ) -> None:
        super().__init__(
            config=config,
            package=package,
            datasources=datasources,
            transactions=transactions,
        )
        self.logger = logger
        self.hook_config = hook_config

    @classmethod
    def _wrap(
        cls,
        ctx: DipDupContext,
        logger: FormattedLogger,
        hook_config: HookConfig,
    ) -> HookContext:
        new_ctx = cls(
            config=ctx.config,
            package=ctx.package,
            datasources=ctx.datasources,
            transactions=ctx.transactions,
            logger=logger,
            hook_config=hook_config,
        )
        ctx._link(new_ctx)
        return new_ctx


class _TemplateValues(dict[str, Any]):
    def __init__(self, index: str, values: Any) -> None:
        self._index = index
        super().__init__(values)

    def __getitem__(self, key: str) -> Any:
        try:
            return dict.__getitem__(self, key)
        except KeyError as e:
            raise ConfigurationError(f'Index `{self._index}` requires `{key}` template value to be set') from e


class HandlerContext(DipDupContext):
    """Execution context of handler callbacks.

    :param handler_config: Configuration of the current handler
    :param datasource: Index datasource instance
    """

    def __init__(
        self,
        config: DipDupConfig,
        package: DipDupPackage,
        datasources: dict[str, Datasource[Any]],
        transactions: TransactionManager,
        logger: FormattedLogger,
        handler_config: HandlerConfig,
        datasource: IndexDatasource[Any],
    ) -> None:
        super().__init__(
            config=config,
            package=package,
            datasources=datasources,
            transactions=transactions,
        )
        self.logger = logger
        self.handler_config = handler_config
        self.datasource = datasource
        self.template_values = _TemplateValues(
            handler_config.parent.name if handler_config.parent else 'unknown',
            handler_config.parent.template_values if handler_config.parent else {},
        )

    @classmethod
    def _wrap(
        cls,
        ctx: DipDupContext,
        logger: FormattedLogger,
        handler_config: HandlerConfig,
        datasource: IndexDatasource[Any],
    ) -> HandlerContext:
        new_ctx = cls(
            config=ctx.config,
            package=ctx.package,
            datasources=ctx.datasources,
            transactions=ctx.transactions,
            logger=logger,
            handler_config=handler_config,
            datasource=datasource,
        )
        ctx._link(new_ctx)
        return new_ctx
