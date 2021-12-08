import asyncio
import logging
from asyncio import CancelledError
from asyncio import Event
from asyncio import Task
from asyncio import create_task
from asyncio import gather
from collections import deque
from contextlib import AsyncExitStack
from contextlib import asynccontextmanager
from contextlib import suppress
from typing import Awaitable
from typing import Deque
from typing import Dict
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple
from typing import cast

from apscheduler.events import EVENT_JOB_ERROR  # type: ignore
from tortoise.exceptions import OperationalError
from tortoise.transactions import get_connection

from dipdup.codegen import DipDupCodeGenerator
from dipdup.config import BcdDatasourceConfig
from dipdup.config import CoinbaseDatasourceConfig
from dipdup.config import ContractConfig
from dipdup.config import DatasourceConfigT
from dipdup.config import DipDupConfig
from dipdup.config import IndexTemplateConfig
from dipdup.config import OperationIndexConfig
from dipdup.config import PostgresDatabaseConfig
from dipdup.config import TzktDatasourceConfig
from dipdup.config import default_hooks
from dipdup.context import CallbackManager
from dipdup.context import DipDupContext
from dipdup.context import pending_indexes
from dipdup.datasources.bcd.datasource import BcdDatasource
from dipdup.datasources.coinbase.datasource import CoinbaseDatasource
from dipdup.datasources.datasource import Datasource
from dipdup.datasources.datasource import IndexDatasource
from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.enums import ReindexingReason
from dipdup.exceptions import ConfigInitializationException
from dipdup.exceptions import DipDupException
from dipdup.exceptions import ReindexingRequiredError
from dipdup.hasura import HasuraGateway
from dipdup.index import BigMapIndex
from dipdup.index import HeadIndex
from dipdup.index import Index
from dipdup.index import OperationIndex
from dipdup.index import block_cache
from dipdup.index import extract_operation_subgroups
from dipdup.index import head_cache
from dipdup.models import BigMapData
from dipdup.models import Contract
from dipdup.models import Head
from dipdup.models import HeadBlockData
from dipdup.models import Index as IndexState
from dipdup.models import IndexStatus
from dipdup.models import OperationData
from dipdup.models import Schema
from dipdup.scheduler import add_job
from dipdup.scheduler import create_scheduler
from dipdup.utils import slowdown
from dipdup.utils.database import generate_schema
from dipdup.utils.database import get_schema_hash
from dipdup.utils.database import prepare_models
from dipdup.utils.database import set_schema
from dipdup.utils.database import tortoise_wrapper
from dipdup.utils.database import validate_models


class IndexDispatcher:
    def __init__(self, ctx: DipDupContext) -> None:
        self._ctx = ctx

        self._logger = logging.getLogger('dipdup')
        self._indexes: Dict[str, Index] = {}
        self._contracts: Set[ContractConfig] = set()
        self._stopped: bool = False
        self._tasks: Deque[asyncio.Task] = deque()

        self._entrypoint_filter: Set[Optional[str]] = set()
        self._address_filter: Set[str] = set()

    async def run(
        self,
        spawn_datasources_event: Event,
        start_scheduler_event: Event,
        early_realtime: bool = False,
    ) -> None:
        self._logger.info('Starting index dispatcher')
        await self._subscribe_to_datasource_events()
        await self._load_index_states()

        on_synchronized_fired = False

        for index in self._indexes.values():
            if isinstance(index, OperationIndex):
                self._apply_filters(index._config)

        while not self._stopped:
            if not spawn_datasources_event.is_set():
                if self._every_index_is(IndexStatus.REALTIME) or early_realtime:
                    spawn_datasources_event.set()

            if spawn_datasources_event.is_set():
                index_datasources = set(i.datasource for i in self._indexes.values())
                for datasource in index_datasources:
                    await datasource.subscribe()

            tasks: Deque[Awaitable] = deque(index.process() for index in self._indexes.values())
            while self._tasks:
                tasks.append(self._tasks.popleft())

            async with slowdown(1):
                await gather(*tasks)

            indexes_spawned = False
            while pending_indexes:
                index = pending_indexes.popleft()
                self._indexes[index._config.name] = index
                indexes_spawned = True

                if isinstance(index, OperationIndex):
                    self._apply_filters(index._config)

            if not indexes_spawned and self._every_index_is(IndexStatus.ONESHOT):
                self.stop()

            if self._every_index_is(IndexStatus.REALTIME) and not indexes_spawned:
                if not on_synchronized_fired:
                    on_synchronized_fired = True
                    await self._ctx.fire_hook('on_synchronized')

                if not start_scheduler_event.is_set():
                    start_scheduler_event.set()
            # NOTE: Fire `on_synchronized` hook when indexes will reach realtime state again
            else:
                on_synchronized_fired = False

    def stop(self) -> None:
        self._stopped = True

    def _apply_filters(self, index_config: OperationIndexConfig) -> None:
        self._address_filter.update(index_config.address_filter)
        self._entrypoint_filter.update(index_config.entrypoint_filter)

    def _every_index_is(self, status: IndexStatus) -> bool:
        if not self._indexes:
            return False

        statuses = set(i.state.status for i in self._indexes.values())
        return statuses == {status}

    async def _fetch_contracts(self) -> None:
        """Add contracts spawned from context to config"""
        contracts = await Contract.filter().all()
        self._logger.info('%s contracts fetched from database', len(contracts))

        for contract in contracts:
            if contract.name not in self._ctx.config.contracts:
                contract_config = ContractConfig(address=contract.address, typename=contract.typename)
                self._ctx.config.contracts[contract.name] = contract_config
        self._ctx.config.initialize(skip_imports=True)

    async def _subscribe_to_datasource_events(self) -> None:
        for datasource in self._ctx.datasources.values():
            if not isinstance(datasource, IndexDatasource):
                continue
            # NOTE: No need to subscribe to head, handled by datasource itself
            # FIXME: mypy tricks, ignore first argument
            datasource.on_head(self._on_head)  # type: ignore
            datasource.on_operations(self._on_operations)  # type: ignore
            datasource.on_big_maps(self._on_big_maps)  # type: ignore
            datasource.on_rollback(self._on_rollback)  # type: ignore

    async def _load_index_states(self) -> None:
        if self._indexes:
            raise RuntimeError('Index states are already loaded')

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
                    index_state.config_hash = new_hash  # type: ignore
                    await index_state.save()
                elif new_hash != index_state.config_hash:
                    await self._ctx.reindex(
                        ReindexingReason.CONFIG_HASH_MISMATCH,
                        old_hash=index_state.config_hash,
                        new_hash=new_hash,
                    )

            # NOTE: Templated index: recreate index config, verify hash
            elif template:
                if template not in self._ctx.config.templates:
                    await self._ctx.reindex(
                        ReindexingReason.MISSING_INDEX_TEMPLATE,
                        index_name=index_state.name,
                        template=template,
                    )
                await self._ctx.add_index(name, template, template_values, index_state)

            # NOTE: Index config is missing, possibly just commented-out
            else:
                self._logger.warning('Index `%s` was removed from config, ignoring', name)

        tasks = (create_task(_process(index_state)) for index_state in await IndexState.all())
        await gather(*tasks)

        # NOTE: Cached blocks used only on index state init
        block_cache.clear()
        head_cache.clear()

    async def _on_head(self, datasource: TzktDatasource, head: HeadBlockData) -> None:
        # NOTE: Do not await query results - blocked database connection may cause Websocket timeout.
        self._tasks.append(
            asyncio.create_task(
                Head.update_or_create(
                    name=datasource.name,
                    defaults=dict(
                        level=head.level,
                        hash=head.hash,
                        timestamp=head.timestamp,
                    ),
                ),
            )
        )
        for index in self._indexes.values():
            if isinstance(index, HeadIndex) and index.datasource == datasource:
                index.push_head(head)

    async def _on_operations(self, datasource: TzktDatasource, operations: Tuple[OperationData, ...]) -> None:
        operation_subgroups = tuple(
            extract_operation_subgroups(
                operations,
                entrypoints=self._entrypoint_filter,
                addresses=self._address_filter,
            )
        )

        if not operation_subgroups:
            return

        operation_indexes = (i for i in self._indexes.values() if isinstance(i, OperationIndex) and i.datasource == datasource)
        for index in operation_indexes:
            index.push_operations(operation_subgroups)

    async def _on_big_maps(self, datasource: TzktDatasource, big_maps: Tuple[BigMapData]) -> None:
        big_map_indexes = (i for i in self._indexes.values() if isinstance(i, BigMapIndex) and i.datasource == datasource)
        for index in big_map_indexes:
            index.push_big_maps(big_maps)

    async def _on_rollback(self, datasource: TzktDatasource, from_level: int, to_level: int) -> None:
        """Perform a single level rollback when possible, otherwise call `on_rollback` hook"""
        self._logger.warning('Datasource `%s` rolled back: %s -> %s', datasource.name, from_level, to_level)

        # NOTE: Zero difference between levels means we received no operations/big_maps on this level and thus channel level hasn't changed
        zero_level_rollback = from_level - to_level == 0
        single_level_rollback = from_level - to_level == 1

        if zero_level_rollback:
            self._logger.info('Zero level rollback, ignoring')

        elif single_level_rollback:
            # NOTE: Notify all indexes which use rolled back datasource to drop duplicated operations from the next block
            self._logger.info('Checking if single level rollback is possible')
            matching_indexes = tuple(i for i in self._indexes.values() if i.datasource == datasource)
            matching_operation_indexes = tuple(i for i in matching_indexes if isinstance(i, OperationIndex))
            self._logger.info(
                'Indexes: %s total, %s matching, %s support single level rollback',
                len(self._indexes),
                len(matching_indexes),
                len(matching_operation_indexes),
            )

            all_indexes_are_operation = len(matching_indexes) == len(matching_operation_indexes)
            if all_indexes_are_operation:
                for index in cast(List[OperationIndex], matching_indexes):
                    index.push_rollback(from_level)
            else:
                await self._ctx.fire_hook('on_rollback', datasource=datasource, from_level=from_level, to_level=to_level)

        else:
            await self._ctx.fire_hook('on_rollback', datasource=datasource, from_level=from_level, to_level=to_level)


class DipDup:
    """Main indexer class.

    Spawns datasources, registers indexes, passes handler callbacks to executor"""

    def __init__(self, config: DipDupConfig) -> None:
        self._logger = logging.getLogger('dipdup')
        self._config = config
        self._datasources: Dict[str, Datasource] = {}
        self._datasources_by_config: Dict[DatasourceConfigT, Datasource] = {}
        self._callbacks: CallbackManager = CallbackManager(self._config.package)
        self._ctx = DipDupContext(
            config=self._config,
            datasources=self._datasources,
            callbacks=self._callbacks,
        )
        self._index_dispatcher: Optional[IndexDispatcher] = None
        self._scheduler = create_scheduler()
        self._codegen = DipDupCodeGenerator(self._config, self._datasources_by_config)
        self._schema: Optional[Schema] = None

    @property
    def schema(self) -> Schema:
        if self._schema is None:
            raise DipDupException('Schema is not initialized')
        return self._schema

    async def init(self, overwrite_types: bool = True) -> None:
        """Create new or update existing dipdup project"""
        await self._create_datasources()

        async with AsyncExitStack() as stack:
            for datasource in self._datasources.values():
                await stack.enter_async_context(datasource)

            await self._codegen.init(overwrite_types)

    async def docker_init(self, image: str, tag: str, env_file: str) -> None:
        await self._codegen.docker_init(image, tag, env_file)

    async def run(self) -> None:
        """Run indexing process"""
        advanced_config = self._config.advanced
        tasks: Set[Task] = set()
        async with AsyncExitStack() as stack:
            stack.enter_context(suppress(KeyboardInterrupt, CancelledError))
            await self._set_up_database(stack)
            await self._set_up_datasources(stack)
            await self._set_up_hooks()

            await self._initialize_schema()
            await self._initialize_datasources()
            await self._set_up_hasura(stack, tasks)

            if self._config.oneshot:
                start_scheduler_event, spawn_datasources_event = Event(), Event()
            else:
                start_scheduler_event = await self._set_up_scheduler(stack, tasks)
                if not advanced_config.postpone_jobs:
                    start_scheduler_event.set()
                spawn_datasources_event = await self._spawn_datasources(tasks)

            spawn_index_tasks = (create_task(self._ctx.spawn_index(name)) for name in self._config.indexes)
            await gather(*spawn_index_tasks)

            await self._set_up_index_dispatcher(tasks, spawn_datasources_event, start_scheduler_event, advanced_config.early_realtime)

            await gather(*tasks)

    async def _create_datasources(self) -> None:
        datasource: Datasource
        for name, datasource_config in self._config.datasources.items():
            if name in self._datasources:
                continue

            if isinstance(datasource_config, TzktDatasourceConfig):
                datasource = TzktDatasource(
                    url=datasource_config.url,
                    http_config=datasource_config.http,
                    merge_subscriptions=self._config.advanced.merge_subscriptions,
                )
            elif isinstance(datasource_config, BcdDatasourceConfig):
                datasource = BcdDatasource(
                    url=datasource_config.url,
                    network=datasource_config.network,
                    http_config=datasource_config.http,
                )
            elif isinstance(datasource_config, CoinbaseDatasourceConfig):
                datasource = CoinbaseDatasource(
                    http_config=datasource_config.http,
                )
            else:
                raise NotImplementedError

            datasource.set_logger(datasource_config.name)
            datasource.set_user_agent(self._config.package)
            self._datasources[name] = datasource
            self._datasources_by_config[datasource_config] = datasource

    async def _initialize_schema(self) -> None:
        self._logger.info('Initializing database schema')
        schema_name = self._config.schema_name
        conn = get_connection(None)

        if isinstance(self._config.database, PostgresDatabaseConfig):
            await set_schema(conn, schema_name)

        # NOTE: Try to fetch existing schema
        try:
            self._schema = await Schema.get_or_none(name=schema_name)

        # NOTE: No such table yet
        except OperationalError:
            self._schema = None

        # TODO: Fix Tortoise ORM to raise more specific exception
        except KeyError:
            try:
                # NOTE: A small migration, ReindexingReason became ReversedEnum
                for item in ReindexingReason:
                    await conn.execute_script(f'UPDATE dipdup_schema SET reindex = "{item.name}" WHERE reindex = "{item.value}"')

                self._schema = await Schema.get_or_none(name=schema_name)
            except KeyError:
                await self._ctx.reindex(ReindexingReason.SCHEMA_HASH_MISMATCH)

        schema_hash = get_schema_hash(conn)

        if self._schema is None:
            await generate_schema(conn, schema_name)
            await self._ctx.fire_hook('on_reindex')

            self._schema = Schema(
                name=schema_name,
                hash=schema_hash,
            )
            try:
                await self._schema.save()
            except OperationalError:
                await self._ctx.reindex(ReindexingReason.SCHEMA_HASH_MISMATCH)

        elif not self._schema.hash:
            self._schema.hash = schema_hash  # type: ignore
            await self._schema.save()

        elif self._schema.hash != schema_hash:
            await self._ctx.reindex(ReindexingReason.SCHEMA_HASH_MISMATCH)

        elif self._schema.reindex:
            raise ReindexingRequiredError(self._schema.reindex)

        await self._ctx.fire_hook('on_restart')

    async def _set_up_database(self, stack: AsyncExitStack) -> None:
        # NOTE: Must be called before entering Tortoise context
        prepare_models(self._config.package)
        validate_models(self._config.package)

        url = self._config.database.connection_string
        timeout = self._config.database.connection_timeout if isinstance(self._config.database, PostgresDatabaseConfig) else None
        models = f'{self._config.package}.models'
        await stack.enter_async_context(tortoise_wrapper(url, models, timeout or 60))

    async def _set_up_hooks(self) -> None:
        for hook_config in default_hooks.values():
            self._ctx.callbacks.register_hook(hook_config)
        for hook_config in self._config.hooks.values():
            self._ctx.callbacks.register_hook(hook_config)

    async def _set_up_hasura(self, stack: AsyncExitStack, tasks: Set[Task]) -> None:
        if not self._config.hasura:
            return

        if not isinstance(self._config.database, PostgresDatabaseConfig):
            raise RuntimeError
        hasura_gateway = HasuraGateway(self._config.package, self._config.hasura, self._config.database)
        await stack.enter_async_context(hasura_gateway)
        tasks.add(create_task(hasura_gateway.configure()))

    async def _set_up_datasources(self, stack: AsyncExitStack) -> None:
        await self._create_datasources()
        for datasource in self._datasources.values():
            await stack.enter_async_context(datasource)

    async def _initialize_datasources(self) -> None:
        for datasource in self._datasources.values():
            if not isinstance(datasource, TzktDatasource):
                continue

            datasource.set_sync_level(
                subscription=None,
                level=(await datasource.get_head_block()).level,
            )

            db_head = await Head.filter(name=datasource.name).first()
            if not db_head:
                continue

            actual_head = await datasource.get_block(db_head.level)
            if db_head.hash != actual_head.hash:
                await self._ctx.reindex(
                    ReindexingReason.BLOCK_HASH_MISMATCH,
                    hash=db_head.hash,
                    actual_hash=actual_head.hash,
                )

    async def _set_up_index_dispatcher(
        self,
        tasks: Set[Task],
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

    async def _spawn_datasources(self, tasks: Set[Task]) -> Event:
        event = Event()

        async def _event_wrapper():
            self._logger.info('Waiting for indexes to synchronize before spawning datasources')
            await event.wait()

            self._logger.info('Spawning datasources')
            _tasks = [create_task(d.run()) for d in self._datasources.values()]
            await gather(*_tasks)

        tasks.add(create_task(_event_wrapper()))
        return event

    async def _set_up_scheduler(self, stack: AsyncExitStack, tasks: Set[Task]) -> Event:
        job_failed = Event()
        event = Event()
        exception: Optional[Exception] = None

        @asynccontextmanager
        async def _context():
            try:
                self._scheduler.start()
                yield
            finally:
                self._scheduler.shutdown()

        def _error_hook(event) -> None:
            nonlocal job_failed, exception
            exception = event.exception
            job_failed.set()

        async def _watchdog() -> None:
            nonlocal job_failed
            await job_failed.wait()
            if not isinstance(exception, Exception):
                raise RuntimeError
            raise exception

        async def _event_wrapper():
            self._logger.info('Waiting for an event to start scheduler')
            await event.wait()

            self._logger.info('Starting scheduler')
            self._scheduler.add_listener(_error_hook, EVENT_JOB_ERROR)
            await stack.enter_async_context(_context())
            tasks.add(create_task(_watchdog()))

            for job_config in self._config.jobs.values():
                add_job(self._ctx, self._scheduler, job_config)

        tasks.add(create_task(_event_wrapper()))
        return event
