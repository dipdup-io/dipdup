import asyncio
import logging
from asyncio import CancelledError
from asyncio import Event
from asyncio import Task
from asyncio import create_task
from asyncio import gather
from collections import deque
from contextlib import AsyncExitStack
from contextlib import suppress
from copy import copy
from typing import Any
from typing import Awaitable
from typing import Dict
from typing import Optional

from tortoise.exceptions import OperationalError

from dipdup.codegen import CodeGenerator
from dipdup.config import ContractConfig
from dipdup.config import DatasourceConfigU
from dipdup.config import DipDupConfig
from dipdup.config import IndexTemplateConfig
from dipdup.config import PostgresDatabaseConfig
from dipdup.config import SqliteDatabaseConfig
from dipdup.config import event_hooks
from dipdup.context import CallbackManager
from dipdup.context import DipDupContext
from dipdup.context import MetadataCursor
from dipdup.context import pending_indexes
from dipdup.datasources.datasource import Datasource
from dipdup.datasources.datasource import IndexDatasource
from dipdup.datasources.factory import DatasourceFactory
from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.datasources.tzkt.datasource import resolve_tzkt_code_hashes
from dipdup.enums import IndexStatus
from dipdup.enums import MessageType
from dipdup.enums import ReindexingReason
from dipdup.exceptions import ConfigInitializationException
from dipdup.exceptions import DipDupException
from dipdup.exceptions import FrameworkException
from dipdup.hasura import HasuraGateway
from dipdup.index import Index
from dipdup.indexes.big_map.index import BigMapIndex
from dipdup.indexes.event.index import EventIndex
from dipdup.indexes.head.index import HeadIndex
from dipdup.indexes.operation.index import OperationIndex
from dipdup.indexes.operation.index import extract_operation_subgroups
from dipdup.indexes.token_transfer.index import TokenTransferIndex
from dipdup.models import BigMapData
from dipdup.models import Contract
from dipdup.models import EventData
from dipdup.models import Head
from dipdup.models import HeadBlockData
from dipdup.models import Index as IndexState
from dipdup.models import OperationData
from dipdup.models import Schema
from dipdup.models import TokenTransferData
from dipdup.models import TzktRollbackMessage
from dipdup.prometheus import Metrics
from dipdup.scheduler import SchedulerManager
from dipdup.transactions import TransactionManager
from dipdup.utils.database import generate_schema
from dipdup.utils.database import get_connection
from dipdup.utils.database import get_schema_hash
from dipdup.utils.database import tortoise_wrapper


class IndexDispatcher:
    def __init__(self, ctx: DipDupContext) -> None:
        self._ctx = ctx

        self._logger = logging.getLogger('dipdup')
        self._indexes: Dict[str, Index[Any, Any, Any]] = {}

        self._entrypoint_filter: set[str | None] = set()
        self._address_filter: set[str] = set()
        self._code_hash_filter: set[int] = set()

    async def run(
        self,
        spawn_datasources_event: Event,
        start_scheduler_event: Event,
        early_realtime: bool = False,
    ) -> None:
        self._logger.info('Starting index dispatcher')
        await self._subscribe_to_datasource_events()
        await self._load_index_state()

        on_synchronized_fired = False

        for index in self._indexes.values():
            if isinstance(index, OperationIndex):
                await self._apply_filters(index)

        while True:
            if not spawn_datasources_event.is_set():
                if (self._every_index_is(IndexStatus.REALTIME) or early_realtime) and not self._ctx.config.oneshot:
                    spawn_datasources_event.set()

            if spawn_datasources_event.is_set():
                index_datasources = {i.datasource for i in self._indexes.values()}
                for datasource in index_datasources:
                    await datasource.subscribe()

            tasks: deque[Awaitable[bool]] = deque()
            for name, index in copy(self._indexes).items():
                if index.state.status == IndexStatus.ONESHOT:
                    del self._indexes[name]
                    continue

                tasks.append(index.process())

            await gather(*tasks)

            indexes_spawned = False
            while pending_indexes:
                index = pending_indexes.popleft()
                self._indexes[index._config.name] = index
                indexes_spawned = True

                if isinstance(index, OperationIndex):
                    await self._apply_filters(index)

            if not indexes_spawned and (not self._indexes or self._every_index_is(IndexStatus.ONESHOT)):
                self._logger.info('No indexes left, exiting')
                break

            if self._every_index_is(IndexStatus.REALTIME) and not indexes_spawned:
                if not on_synchronized_fired:
                    on_synchronized_fired = True
                    await self._ctx.fire_hook('on_synchronized')

                if not start_scheduler_event.is_set():
                    start_scheduler_event.set()
            else:
                # NOTE: Fire `on_synchronized` hook when indexes will reach realtime state again
                on_synchronized_fired = False

            # TODO: Replace with asyncio.Event
            await asyncio.sleep(1)

    async def _update_metrics(self, update_interval: float) -> None:
        while True:
            await asyncio.sleep(update_interval)

            active, synced, realtime = 0, 0, 0
            for index in tuple(self._indexes.values()) + tuple(pending_indexes):
                active += 1
                if index.synchronized:
                    synced += 1
                if index.realtime:
                    realtime += 1

            Metrics.set_indexes_count(active, synced, realtime)

    async def _apply_filters(self, index: OperationIndex) -> None:
        entrypoints, addresses, code_hashes = await index.get_filters()
        self._entrypoint_filter.update(entrypoints)
        self._address_filter.update(addresses)
        self._code_hash_filter.update(code_hashes)

    def _every_index_is(self, status: IndexStatus) -> bool:
        if not self._indexes:
            return False

        statuses = {i.state.status for i in self._indexes.values()}
        return statuses == {status}

    async def _fetch_contracts(self) -> None:
        """Add contracts spawned from context to config"""
        contracts = await Contract.filter().all()
        self._logger.info('%s contracts fetched from database', len(contracts))

        for contract in contracts:
            # FIXME: No `code_hash` field in the database
            if ':' in contract.address:
                address, code_hash = contract.address.split(':')
            else:
                address, code_hash = contract.address, None

            if contract.name not in self._ctx.config.contracts:
                contract_config = ContractConfig(
                    address=address or None,
                    code_hash=code_hash or None,
                    typename=contract.typename,
                )
                self._ctx.config.contracts[contract.name] = contract_config

        self._ctx.config.initialize(skip_imports=True)

    async def _load_index_state(self) -> None:
        if self._indexes:
            raise FrameworkException('Index states are already loaded')

        await self._fetch_contracts()
        self._logger.info('%s indexes found in database', await IndexState.all().count())

        async def _process(index_state: IndexState) -> None:
            name, template, template_values = index_state.name, index_state.template, index_state.template_values

            # NOTE: Index in config (templates are already resolved): just verify hash
            if index_config := self._ctx.config.indexes.get(name):
                if isinstance(index_config, IndexTemplateConfig):
                    raise ConfigInitializationException

                new_hash = index_config.hash()
                if not index_state.config_hash:
                    index_state.config_hash = new_hash
                    await index_state.save()
                elif new_hash != index_state.config_hash:
                    await self._ctx.reindex(
                        ReindexingReason.config_modified,
                        old_hash=index_state.config_hash,
                        new_hash=new_hash,
                    )

            # NOTE: Templated index: recreate index config, verify hash
            elif template:
                if template not in self._ctx.config.templates:
                    await self._ctx.reindex(
                        ReindexingReason.config_modified,
                        index_name=index_state.name,
                        template=template,
                    )
                await self._ctx.add_index(
                    name,
                    template,
                    template_values,
                    state=index_state,
                )

            # NOTE: Index config is missing, possibly just commented-out
            else:
                self._logger.warning('Index `%s` not found in config, ignoring', name)

        # FIXME: Outdated optimization
        tasks = (create_task(_process(index_state)) for index_state in await IndexState.all())
        await gather(*tasks)

    async def _subscribe_to_datasource_events(self) -> None:
        for datasource in self._ctx.datasources.values():
            if not isinstance(datasource, IndexDatasource):
                continue
            datasource.call_on_head(self._on_head)
            datasource.call_on_operations(self._on_operations)
            datasource.call_on_token_transfers(self._on_token_transfers)
            datasource.call_on_big_maps(self._on_big_maps)
            datasource.call_on_events(self._on_events)
            datasource.call_on_rollback(self._on_rollback)

    async def _on_head(self, datasource: IndexDatasource, head: HeadBlockData) -> None:
        # NOTE: Do not await query results, it may block Websocket loop. We do not use Head anyway.
        asyncio.ensure_future(
            Head.update_or_create(
                name=datasource.name,
                defaults={
                    'level': head.level,
                    'hash': head.hash,
                    'timestamp': head.timestamp,
                },
            ),
        )
        if Metrics.enabled:
            Metrics.set_datasource_head_updated(datasource.name)
        for index in self._indexes.values():
            if isinstance(index, HeadIndex) and index.datasource == datasource:
                index.push_head(head)

    async def _on_operations(self, datasource: IndexDatasource, operations: tuple[OperationData, ...]) -> None:
        operation_subgroups = tuple(
            extract_operation_subgroups(
                operations,
                addresses=self._address_filter,
                entrypoints=self._entrypoint_filter,
                code_hashes=self._code_hash_filter,
            )
        )

        if not operation_subgroups:
            return

        for index in self._indexes.values():
            if isinstance(index, OperationIndex) and index.datasource == datasource:
                index.push_operations(operation_subgroups)

    async def _on_token_transfers(
        self, datasource: IndexDatasource, token_transfers: tuple[TokenTransferData, ...]
    ) -> None:
        for index in self._indexes.values():
            if isinstance(index, TokenTransferIndex) and index.datasource == datasource:
                index.push_token_transfers(token_transfers)

    async def _on_big_maps(self, datasource: IndexDatasource, big_maps: tuple[BigMapData, ...]) -> None:
        for index in self._indexes.values():
            if isinstance(index, BigMapIndex) and index.datasource == datasource:
                index.push_big_maps(big_maps)

    async def _on_events(self, datasource: IndexDatasource, events: tuple[EventData, ...]) -> None:
        for index in self._indexes.values():
            if isinstance(index, EventIndex) and index.datasource == datasource:
                index.push_events(events)

    async def _on_rollback(
        self,
        datasource: IndexDatasource,
        type_: MessageType,
        from_level: int,
        to_level: int,
    ) -> None:
        """Call `on_index_rollback` hook for each index that is affected by rollback"""
        if from_level <= to_level:
            raise FrameworkException(f'Attempt to rollback forward: {from_level} -> {to_level}')

        channel = f'{datasource.name}:{type_.value}'
        self._logger.info('Channel `%s` has rolled back: %s -> %s', channel, from_level, to_level)
        if Metrics.enabled:
            Metrics.set_datasource_rollback(datasource.name)

        # NOTE: Choose action for each index
        for index_name, index in self._indexes.items():
            index_level = index.state.level

            if index.message_type != type_:
                self._logger.debug('%s: different channel, skipping', index_name)

            elif index.datasource != datasource:
                self._logger.debug('%s: different datasource, skipping', index_name)

            elif to_level >= index_level:
                self._logger.debug('%s: level is too low, skipping', index_name)

            else:
                self._logger.debug('%s: affected', index_name)
                index.push_realtime_message(
                    TzktRollbackMessage(from_level, to_level),
                )

        self._logger.info('`%s` rollback processed', channel)


class DipDup:
    """Main indexer class.

    Spawns datasources, registers indexes, passes handler callbacks to executor"""

    def __init__(self, config: DipDupConfig) -> None:
        self._logger = logging.getLogger('dipdup')
        self._config = config
        self._datasources: Dict[str, Datasource] = {}
        self._datasources_by_config: Dict[DatasourceConfigU, Datasource] = {}
        self._callbacks: CallbackManager = CallbackManager(self._config.package)
        self._transactions: TransactionManager = TransactionManager(
            depth=self._config.advanced.rollback_depth,
            immune_tables=self._config.database.immune_tables,
        )
        self._ctx = DipDupContext(
            config=self._config,
            datasources=self._datasources,
            callbacks=self._callbacks,
            transactions=self._transactions,
        )
        self._codegen = CodeGenerator(self._config, self._datasources_by_config)
        self._schema: Optional[Schema] = None

    @property
    def schema(self) -> Schema:
        if self._schema is None:
            raise DipDupException('Schema is not initialized')
        return self._schema

    @classmethod
    async def create_dummy(
        cls,
        config: DipDupConfig,
        stack: AsyncExitStack,
        in_memory: bool = False,
    ) -> 'DipDup':
        """Create a dummy DipDup instance for testing purposes.

        Only basic initialization is performed:

          - Create datasources without spawning them
          - Register event hooks
          - Initialize Tortoise ORM and create schema

        You need to enter `AsyncExitStack` context manager prior to calling this method.
        """
        if in_memory:
            config.database = SqliteDatabaseConfig(
                kind='sqlite',
                path=':memory:',
            )
        config.initialize(skip_imports=True)

        dipdup = DipDup(config)
        await dipdup._create_datasources()
        await dipdup._set_up_database(stack)
        await dipdup._set_up_hooks(set())
        await dipdup._initialize_schema()
        await dipdup._set_up_transactions(stack)

        return dipdup

    async def init(self, overwrite_types: bool = False, keep_schemas: bool = False) -> None:
        """Create new or update existing dipdup project"""
        await self._create_datasources()

        async with AsyncExitStack() as stack:
            for datasource in self._datasources.values():
                await stack.enter_async_context(datasource)

            await self._codegen.init(overwrite_types, keep_schemas)

    async def run(self) -> None:
        """Run indexing process"""
        advanced_config = self._config.advanced
        tasks: set[Task[None]] = set()
        async with AsyncExitStack() as stack:
            stack.enter_context(suppress(KeyboardInterrupt, CancelledError))
            await self._set_up_database(stack)
            await self._set_up_transactions(stack)
            await self._set_up_datasources(stack)
            await self._set_up_hooks(tasks, run=not self._config.oneshot)
            await self._set_up_prometheus()

            await self._initialize_schema()
            await self._initialize_datasources()

            hasura_gateway = await self._set_up_hasura(stack)
            if hasura_gateway:
                await hasura_gateway.configure()

            if advanced_config.metadata_interface:
                await MetadataCursor.initialize()

            if self._config.oneshot:
                start_scheduler_event = Event()
                spawn_datasources_event = Event()

                if self._config.jobs:
                    self._logger.warning('Running in oneshot mode; `jobs` are ignored')
            else:
                start_scheduler_event = await self._set_up_scheduler(tasks)
                spawn_datasources_event = await self._spawn_datasources(tasks)

                if not advanced_config.postpone_jobs:
                    start_scheduler_event.set()

                tasks.add(create_task(self._transactions.cleanup_loop()))

            spawn_index_tasks = (create_task(self._ctx._spawn_index(name)) for name in self._config.indexes)
            await gather(*spawn_index_tasks)

            await self._set_up_index_dispatcher(
                tasks, spawn_datasources_event, start_scheduler_event, advanced_config.early_realtime
            )

            await gather(*tasks)

    async def _create_datasources(self) -> None:
        datasource: Datasource
        for name, datasource_config in self._config.datasources.items():
            if name in self._datasources:
                continue

            datasource = DatasourceFactory.build(name, self._config)

            self._datasources[name] = datasource
            self._datasources_by_config[datasource_config] = datasource

    async def _initialize_schema(self) -> None:
        self._logger.info('Initializing database schema')
        schema_name = self._config.schema_name
        conn = get_connection()

        # NOTE: Try to fetch existing schema, but don't fail yet
        with suppress(OperationalError):
            self._schema = await Schema.get_or_none(name=schema_name)

        # NOTE: Call with existing Schema too to create new tables if missing
        try:
            await generate_schema(
                conn,
                schema_name,
            )
        except OperationalError:
            await self._ctx.reindex(ReindexingReason.schema_modified)

        schema_hash = get_schema_hash(conn)

        if self._schema is None:
            await self._ctx.fire_hook('on_reindex')

            self._schema = Schema(
                name=schema_name,
                hash=schema_hash,
            )
            try:
                await self._schema.save()
            except OperationalError:
                await self._ctx.reindex(ReindexingReason.schema_modified)

        elif not self._schema.hash:
            self._schema.hash = schema_hash
            await self._schema.save()

        elif self._schema.hash != schema_hash:
            await self._ctx.reindex(ReindexingReason.schema_modified)

        elif self._schema.reindex:
            await self._ctx.reindex(self._schema.reindex)

        await self._ctx.fire_hook('on_restart')

    async def _set_up_transactions(self, stack: AsyncExitStack) -> None:
        await stack.enter_async_context(self._transactions.register())

    async def _set_up_database(self, stack: AsyncExitStack) -> None:
        await stack.enter_async_context(
            tortoise_wrapper(
                url=self._config.database.connection_string,
                models=self._config.package,
                timeout=self._config.database.connection_timeout,
                decimal_precision=self._config.advanced.decimal_precision,
            )
        )

    async def _set_up_hooks(self, tasks: set[Task[None]], run: bool = False) -> None:
        for event_hook_config in event_hooks.values():
            self._callbacks.register_hook(event_hook_config)

        for hook_config in self._config.hooks.values():
            self._callbacks.register_hook(hook_config)

        if run:
            tasks.add(create_task(self._callbacks.run()))

    async def _set_up_prometheus(self) -> None:
        if self._config.prometheus:
            from prometheus_client import start_http_server

            Metrics.enabled = True
            start_http_server(self._config.prometheus.port, self._config.prometheus.host)

    async def _set_up_hasura(self, stack: AsyncExitStack) -> HasuraGateway | None:
        if not self._config.hasura:
            return None

        if not isinstance(self._config.database, PostgresDatabaseConfig):
            raise FrameworkException('PostgresDatabaseConfig expected; check earlier')

        hasura_gateway = HasuraGateway(
            self._config.package,
            self._config.hasura,
            self._config.database,
        )
        await stack.enter_async_context(hasura_gateway)
        return hasura_gateway

    async def _set_up_datasources(self, stack: AsyncExitStack) -> None:
        await self._create_datasources()
        for datasource in self._datasources.values():
            await stack.enter_async_context(datasource)

    async def _initialize_datasources(self) -> None:
        for datasource in self._datasources.values():
            if not isinstance(datasource, TzktDatasource):
                continue

            head_block = await datasource.get_head_block()
            datasource.set_network(head_block.chain)
            datasource.set_sync_level(
                subscription=None,
                level=head_block.level,
            )

            db_head = await Head.filter(name=datasource.name).first()
            if not db_head:
                continue

            # NOTE: Ensure that no reorgs happened while we were offline
            actual_head = await datasource.get_block(db_head.level)
            if db_head.hash != actual_head.hash:
                await self._ctx.reindex(
                    ReindexingReason.rollback,
                    datasource=datasource.name,
                    level=db_head.level,
                    stored_block_hash=db_head.hash,
                    actual_block_hash=actual_head.hash,
                )

        await resolve_tzkt_code_hashes(self._config, self._datasources)

    async def _set_up_index_dispatcher(
        self,
        tasks: set[Task[None]],
        spawn_datasources_event: Event,
        start_scheduler_event: Event,
        early_realtime: bool,
    ) -> None:
        index_dispatcher = IndexDispatcher(self._ctx)
        tasks.add(
            create_task(
                index_dispatcher.run(
                    spawn_datasources_event,
                    start_scheduler_event,
                    early_realtime,
                )
            )
        )
        if prometheus_config := self._ctx.config.prometheus:
            tasks.add(create_task(index_dispatcher._update_metrics(prometheus_config.update_interval)))

    async def _spawn_datasources(self, tasks: set[Task[None]]) -> Event:
        event = Event()

        async def _event_wrapper() -> None:
            self._logger.info('Waiting for indexes to synchronize before spawning datasources')
            await event.wait()

            self._logger.info('Spawning datasources')
            _tasks = [create_task(d.run()) for d in self._datasources.values()]
            await gather(*_tasks)

        tasks.add(create_task(_event_wrapper()))
        return event

    async def _set_up_scheduler(self, tasks: set[Task[None]]) -> Event:
        # NOTE: Prepare SchedulerManager
        event = Event()
        scheduler = SchedulerManager(self._config.advanced.scheduler)
        run_task = create_task(scheduler.run(event))
        tasks.add(run_task)

        # NOTE: Register jobs
        for job_config in self._config.jobs.values():
            scheduler.add_job(self._ctx, job_config)

        return event
