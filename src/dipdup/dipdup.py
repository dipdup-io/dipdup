import asyncio
import hashlib
import importlib
import logging
from collections import deque
from os.path import join
from posix import listdir
from typing import Awaitable, Deque, Dict, List, cast

from genericpath import exists
from tortoise import Tortoise
from tortoise.exceptions import OperationalError
from tortoise.transactions import in_transaction
from tortoise.utils import get_schema_sql

import dipdup.utils as utils
from dipdup import __version__
from dipdup.codegen import DipDupCodeGenerator
from dipdup.config import (
    BcdDatasourceConfig,
    BigMapIndexConfig,
    DatasourceConfigT,
    DipDupConfig,
    IndexConfigTemplateT,
    PostgresDatabaseConfig,
    StaticTemplateConfig,
    TzktDatasourceConfig,
)
from dipdup.datasources import DatasourceT
from dipdup.datasources.bcd.datasource import BcdDatasource
from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.hasura import configure_hasura
from dipdup.models import BigMapHandlerContext, IndexType, OperationHandlerContext, State


class CallbackExecutor:
    """Executor for handler callbacks. Used avoid blocking datasource loop."""

    def __init__(self) -> None:
        self._logger = logging.getLogger(f'{__name__}.{self.__class__.__qualname__}')
        self._queue_ready = asyncio.Event()
        self._queue: Deque[Awaitable] = deque()

    def submit(self, fn, *args, **kwargs) -> None:
        """Push coroutine to queue"""
        # TODO: Check fn signature: must return Awaitable[None]
        self._queue_ready.set()
        self._queue.append(fn(*args, **kwargs))

    async def run(self, datasource_tasks: List[asyncio.Task]) -> None:
        """Executor loop"""
        stopping = False
        while True:
            try:
                coro = self._queue.popleft()
                self._logger.info('Executing %s, %s coros left', coro, len(self._queue))
                await coro
            except IndexError:
                if stopping:
                    return
                if all([t.done() for t in datasource_tasks]):
                    self._logger.info('Stopping callback executor loop')
                    return
                self._queue_ready.clear()
                await self._queue_ready.wait()
            except (asyncio.CancelledError, KeyboardInterrupt):
                self._logger.info('Stopping, %s coros left', len(self._queue))
                stopping = True

    async def wait(self, size: int) -> None:
        while len(self._queue) > size:
            await asyncio.sleep(0)


class DipDup:
    """Spawns datasources, processes handler callbacks"""

    def __init__(self, config: DipDupConfig) -> None:
        self._logger = logging.getLogger(__name__)
        self._config = config
        self._spawned_indexes: List[str] = []
        self._executor = CallbackExecutor()
        self._datasources: Dict[str, DatasourceT] = {}
        self._datasources_by_config: Dict[DatasourceConfigT, DatasourceT] = {}

    async def init(self, dynamic: bool) -> None:
        """Create new or update existing dipdup project"""
        self._config.pre_initialize()
        await self._create_datasources()
        codegen = DipDupCodeGenerator(self._config, self._datasources_by_config)
        await codegen.create_package()
        if dynamic:
            await codegen.create_config_module()
        await codegen.fetch_schemas()
        await codegen.generate_types()
        await codegen.generate_handlers()
        await codegen.cleanup()

    async def run(self, reindex: bool) -> None:
        """Main entrypoint"""
        url = self._config.database.connection_string
        models = f'{self._config.package}.models'

        async with utils.tortoise_wrapper(url, models):
            await self._initialize_database(reindex)
            await self._create_datasources()

            if self._config.configuration:
                await self._configure()

            await self._spawn_indexes()

            self._logger.info('Starting datasources')
            datasource_tasks = [asyncio.create_task(d.run()) for d in self._datasources.values()]
            worker_tasks = []

            if self._config.hasura:
                worker_tasks.append(asyncio.create_task(configure_hasura(self._config)))

            worker_tasks.append(asyncio.create_task(self._executor.run(datasource_tasks)))

            try:
                await asyncio.gather(*datasource_tasks, *worker_tasks)
            except (asyncio.CancelledError, KeyboardInterrupt):
                map(lambda t: t.cancel(), worker_tasks + datasource_tasks)

    async def spawn_operation_handler_callback(
        self,
        index_config,
        handler_config,
        args,
        level,
        operations,
    ) -> None:
        self._executor.submit(
            self._operation_handler_callback,
            index_config,
            handler_config,
            args,
            level,
            operations,
        )
        # await self._executor.wait(2000)

    async def spawn_big_map_handler_callback(
        self,
        index_config,
        handler_config,
        args,
        level,
    ):
        self._executor.submit(
            self._big_map_handler_callback,
            index_config,
            handler_config,
            args,
            level,
        )
        # await self._executor.wait(2000)

    async def spawn_rollback_handler_callback(
        self,
        from_level,
        to_level,
    ):
        ...

    async def set_state_level(self, indexes: List[IndexConfigTemplateT], level: int) -> None:
        """Enqueue bumping index state level."""
        for index_config in indexes:
            self._executor.submit(
                self._set_state_level,
                index_config,
                level,
            )

    async def _set_state_level(self, index_config: IndexConfigTemplateT, level: int) -> None:
        index_config.state.level = level  # type: ignore
        await index_config.state.save()


    async def _configure(self) -> None:
        """Run user-defined initial configuration handler"""
        await self._create_datasources()
        config_module = importlib.import_module(f'{self._config.package}.config')
        config_handler = getattr(config_module, 'configure')
        await config_handler(self._config, self._datasources)

    async def _create_datasources(self) -> None:
        datasource: DatasourceT
        for name, datasource_config in self._config.datasources.items():
            if name in self._datasources:
                continue

            if isinstance(datasource_config, TzktDatasourceConfig):
                datasource = TzktDatasource(datasource_config.url, self)

                self._datasources[name] = datasource
                self._datasources_by_config[datasource_config] = datasource

            elif isinstance(datasource_config, BcdDatasourceConfig):
                datasource = BcdDatasource(datasource_config.url, datasource_config.network, self._config.cache_enabled)

                self._datasources[name] = datasource
                self._datasources_by_config[datasource_config] = datasource
            else:
                raise NotImplementedError

    async def _spawn_indexes(self, runtime=False) -> None:
        self._config.pre_initialize()
        await self._config.initialize()

        resync_datasources = []
        for index_name, index_config in self._config.indexes.items():
            if index_name in self._spawned_indexes:
                continue
            if isinstance(index_config, StaticTemplateConfig):
                raise RuntimeError('Config is not pre-initialized')

            self._logger.info('Processing index `%s`', index_name)
            datasource = cast(TzktDatasource, self._datasources_by_config[index_config.datasource_config])
            if datasource not in resync_datasources:
                resync_datasources.append(datasource)

            # NOTE: Actual subscription will be performed after resync
            await datasource.add_index(index_name, index_config)

            self._spawned_indexes.append(index_name)

        if runtime:
            for datasource in resync_datasources:
                await datasource.resync()

    async def _operation_handler_callback(
        self,
        index_config,
        handler_config,
        args,
        level,
        operations,
    ):
        handler_context = OperationHandlerContext(
            datasources=self._datasources,
            config=self._config,
            operations=operations,
            template_values=index_config.template_values,
        )

        async with in_transaction():
            await handler_config.callback_fn(handler_context, *args)

            index_config.state.level = level  # type: ignore
            await index_config.state.save()

        if handler_context.updated:
            await self._spawn_indexes(True)

    async def _big_map_handler_callback(self, index_config: BigMapIndexConfig, handler_config, args, level):
        handler_context = BigMapHandlerContext(
            datasources=self._datasources,
            config=self._config,
            template_values=index_config.template_values,
        )

        async with in_transaction():
            await handler_config.callback_fn(handler_context, *args)

            index_config.state.level = level  # type: ignore
            await index_config.state.save()

        if handler_context.updated:
            await self._spawn_indexes(True)

    async def _rollback_handler_callback(self, from_level, to_level):
        rollback_fn = self._config.get_rollback_fn()
        await rollback_fn(from_level, to_level)

    async def _initialize_database(self, reindex: bool = False) -> None:
        self._logger.info('Initializing database')

        if isinstance(self._config.database, PostgresDatabaseConfig) and self._config.database.schema_name:
            await Tortoise._connections['default'].execute_script(f"CREATE SCHEMA IF NOT EXISTS {self._config.database.schema_name}")
            await Tortoise._connections['default'].execute_script(f"SET search_path TO {self._config.database.schema_name}")

        connection_name, connection = next(iter(Tortoise._connections.items()))
        schema_sql = get_schema_sql(connection, False)

        # NOTE: Column order could differ in two generated schemas for the same models, drop commas and sort strings to eliminate this
        processed_schema_sql = '\n'.join(sorted(schema_sql.replace(',', '').split('\n'))).encode()
        schema_hash = hashlib.sha256(processed_schema_sql).hexdigest()

        if reindex:
            self._logger.warning('Started with `--reindex` argument, reindexing')
            await utils.reindex()

        try:
            schema_state = await State.get_or_none(index_type=IndexType.schema, index_name=connection_name)
        except OperationalError:
            schema_state = None

        if schema_state is None:
            await Tortoise.generate_schemas()
            schema_state = State(index_type=IndexType.schema, index_name=connection_name, hash=schema_hash)
            await schema_state.save()
        elif schema_state.hash != schema_hash:
            self._logger.warning('Schema hash mismatch, reindexing')
            await utils.reindex()

        sql_path = join(self._config.package_path, 'sql')
        if not exists(sql_path):
            return
        if not isinstance(self._config.database, PostgresDatabaseConfig):
            self._logger.warning('Injecting raw SQL supported on PostgreSQL only')
            return

        for filename in listdir(sql_path):
            if not filename.endswith('.sql'):
                continue

            with open(join(sql_path, filename)) as file:
                sql = file.read()

            self._logger.info('Applying raw SQL from `%s`', filename)

            async with in_transaction() as conn:
                await conn.execute_query(sql)
