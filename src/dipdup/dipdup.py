import logging
from asyncio import CancelledError, Event, Task, create_task, gather
from contextlib import AsyncExitStack, asynccontextmanager, suppress
from functools import partial
from operator import ne
from typing import Dict, List, Optional, Set

from apscheduler.events import EVENT_JOB_ERROR  # type: ignore
from tortoise.exceptions import OperationalError
from tortoise.transactions import get_connection

from dipdup.codegen import DipDupCodeGenerator
from dipdup.config import (
    BcdDatasourceConfig,
    CoinbaseDatasourceConfig,
    ContractConfig,
    DatasourceConfigT,
    DipDupConfig,
    IndexTemplateConfig,
    PostgresDatabaseConfig,
    TzktDatasourceConfig,
    default_hooks,
)
from dipdup.context import CallbackManager, DipDupContext, pending_indexes
from dipdup.datasources.bcd.datasource import BcdDatasource
from dipdup.datasources.coinbase.datasource import CoinbaseDatasource
from dipdup.datasources.datasource import Datasource, IndexDatasource
from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.exceptions import ConfigInitializationException, DipDupException, ReindexingRequiredError
from dipdup.hasura import HasuraGateway
from dipdup.index import BigMapIndex, Index, OperationIndex
from dipdup.models import BigMapData, Contract, HeadBlockData
from dipdup.models import Index as IndexState
from dipdup.models import IndexStatus, OperationData, Schema
from dipdup.scheduler import add_job, create_scheduler
from dipdup.utils import FormattedLogger, slowdown
from dipdup.utils.database import generate_schema, get_schema_hash, set_schema, tortoise_wrapper, validate_models


class IndexDispatcher:
    def __init__(self, ctx: DipDupContext) -> None:
        self._ctx = ctx

        self._logger = logging.getLogger('dipdup')
        self._indexes: Dict[str, Index] = {}
        self._contracts: Set[ContractConfig] = set()
        self._stopped: bool = False
        self._synchronized: bool = False

    async def run(self) -> None:
        self._logger.info('Starting index dispatcher')
        await self._subscribe_to_datasources()
        await self._load_index_states()

        while not self._stopped:
            with suppress(IndexError):
                while index := pending_indexes.pop():
                    self._indexes[index._config.name] = index

            tasks = [index.process() for index in self._indexes.values()]
            async with slowdown(1.0):
                await gather(*tasks)

            await self._check_states()

    def stop(self) -> None:
        self._stopped = True

    async def _check_states(self) -> None:
        statuses = [i.state.status for i in self._indexes.values()]

        def _have_no(status: IndexStatus) -> bool:
            nonlocal statuses
            return bool(tuple(filter(partial(ne, status), statuses)))

        synching_indexes = _have_no(IndexStatus.REALTIME)
        if not synching_indexes:
            # TODO: `on_synchronized` hook? Not sure if we need it.
            ...

        pending_oneshot_indexes = _have_no(IndexStatus.ONESHOT)
        if not pending_oneshot_indexes:
            self.stop()

    async def _fetch_contracts(self) -> None:
        """Add contracts spawned from context to config"""
        contracts = await Contract.filter().all()
        self._logger.info('%s contracts fetched from database', len(contracts))

        for contract in contracts:
            if contract.name not in self._ctx.config.contracts:
                contract_config = ContractConfig(address=contract.address, typename=contract.typename)
                self._ctx.config.contracts[contract.name] = contract_config
        self._ctx.config.pre_initialize()

    async def _subscribe_to_datasources(self) -> None:
        for datasource in self._ctx.datasources.values():
            if not isinstance(datasource, IndexDatasource):
                continue
            datasource.on_operations(self._dispatch_operations)
            datasource.on_big_maps(self._dispatch_big_maps)
            datasource.on_rollback(self._rollback)

    async def _load_index_states(self) -> None:
        await self._fetch_contracts()
        index_states = await IndexState.filter().all()
        self._logger.info('%s indexes found in database', len(index_states))
        for index_state in index_states:
            name, template, template_values = index_state.name, index_state.template, index_state.template_values
            if name in self._indexes:
                raise RuntimeError

            if index_config := self._ctx.config.indexes.get(name):
                if isinstance(index_config, IndexTemplateConfig):
                    raise ConfigInitializationException
                if index_config.hash() != index_state.config_hash:
                    await self._ctx.reindex(reason='config has been modified')

            elif template:
                if template not in self._ctx.config.templates:
                    await self._ctx.reindex(reason=f'template `{template}` has been removed from config')
                await self._ctx.add_index(name, template, template_values)

            else:
                self._logger.warning('Index `%s` was removed from config, ignoring', name)

    async def _dispatch_operations(self, datasource: TzktDatasource, operations: List[OperationData], block: HeadBlockData) -> None:
        assert len(set(op.level for op in operations)) == 1
        level = operations[0].level
        for index in self._indexes.values():
            if isinstance(index, OperationIndex) and index.datasource == datasource:
                index.push(level, operations, block)

    async def _dispatch_big_maps(self, datasource: TzktDatasource, big_maps: List[BigMapData], block: HeadBlockData) -> None:
        assert len(set(op.level for op in big_maps)) == 1
        level = big_maps[0].level
        for index in self._indexes.values():
            if isinstance(index, BigMapIndex) and index.datasource == datasource:
                index.push(level, big_maps, block)

    async def _rollback(self, datasource: TzktDatasource, from_level: int, to_level: int) -> None:
        if from_level - to_level == 1:
            # NOTE: Single level rollbacks are processed at Index level.
            # NOTE: Notify all indexes which use rolled back datasource to drop duplicated operations from the next block
            for index in self._indexes.values():
                if index.datasource == datasource:
                    # NOTE: Continue to rollback with handler
                    if not isinstance(index, OperationIndex):
                        self._logger.info('Single level rollback is not supported by `%s` indexes', index._config.kind)
                        break
                    await index.single_level_rollback(from_level)
            else:
                return

        await self._ctx.fire_hook('on_rollback', datasource, from_level, to_level)


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

    async def run(self, reindex: bool, oneshot: bool) -> None:
        """Run indexing process"""
        tasks: Set[Task] = set()
        async with AsyncExitStack() as stack:
            stack.enter_context(suppress(KeyboardInterrupt, CancelledError))
            await self._set_up_database(stack, reindex)
            await self._set_up_datasources(stack)
            await self._set_up_hooks()

            await self._initialize_schema()
            await self._set_up_hasura(stack, tasks)

            if not oneshot:
                await self._set_up_scheduler(stack, tasks)
                await self._spawn_datasources(tasks)

            for name in self._config.indexes:
                await self._ctx._spawn_index(name)

            await self._set_up_index_dispatcher(tasks)

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

            datasource._logger = FormattedLogger(datasource._logger.name, datasource_config.name + ': {}')
            datasource.set_user_agent(self._config.package)
            self._datasources[name] = datasource
            self._datasources_by_config[datasource_config] = datasource

    async def _initialize_schema(self) -> None:
        self._logger.info('Initializing database schema')
        schema_name = 'public'
        conn = get_connection(None)

        if isinstance(self._config.database, PostgresDatabaseConfig):
            schema_name = self._config.database.schema_name
            await set_schema(conn, schema_name)

        try:
            self._schema = await Schema.get_or_none(name=schema_name)
        except OperationalError:
            self._schema = None
        # TODO: Fix Tortoise ORM to raise more specific exception
        except KeyError as e:
            raise ReindexingRequiredError from e

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
            except OperationalError as e:
                raise ReindexingRequiredError from e

        elif self._schema.hash != schema_hash:
            await self._ctx.reindex(reason='schema hash mismatch')

        await self._ctx.fire_hook('on_restart')

    async def _set_up_database(self, stack: AsyncExitStack, reindex: bool) -> None:
        # NOTE: Must be called before Tortoise.init
        validate_models(self._config.package)

        url = self._config.database.connection_string
        timeout = self._config.database.connection_timeout if isinstance(self._config.database, PostgresDatabaseConfig) else None
        models = f'{self._config.package}.models'
        await stack.enter_async_context(tortoise_wrapper(url, models, timeout or 60))

        if reindex:
            await self._ctx.reindex(reason='run with `--reindex` option')

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
        # FIXME: Find a better way to do this
        # if self._datasources:
        #     raise RuntimeError
        await self._create_datasources()
        for datasource in self._datasources.values():
            await stack.enter_async_context(datasource)

    async def _set_up_index_dispatcher(self, tasks: Set[Task]) -> None:
        index_dispatcher = IndexDispatcher(self._ctx)
        tasks.add(create_task(index_dispatcher.run()))

    async def _spawn_datasources(self, tasks: Set[Task]) -> None:
        tasks.update(create_task(d.run()) for d in self._datasources.values())

    async def _set_up_scheduler(self, stack: AsyncExitStack, tasks: Set[Task]) -> None:
        job_failed = Event()
        exception: Optional[Exception] = None

        @asynccontextmanager
        async def _context():
            try:
                yield
            finally:
                self._scheduler.shutdown()

        def _hook(event) -> None:
            nonlocal job_failed, exception
            exception = event.exception
            job_failed.set()

        async def _watchdog() -> None:
            nonlocal job_failed
            await job_failed.wait()
            raise exception  # type: ignore

        await stack.enter_async_context(_context())
        tasks.add(create_task(_watchdog()))

        for job_config in self._config.jobs.values():
            add_job(self._ctx, self._scheduler, job_config)

        self._scheduler.add_listener(_hook, EVENT_JOB_ERROR)
        self._scheduler.start()
