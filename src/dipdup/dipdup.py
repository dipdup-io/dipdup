import asyncio
import hashlib
import logging
from contextlib import suppress
from os.path import join
from posix import listdir
from typing import Dict, List, cast

from aiolimiter import AsyncLimiter
from apscheduler.schedulers import SchedulerNotRunningError  # type: ignore
from genericpath import exists
from tortoise import Tortoise
from tortoise.exceptions import OperationalError
from tortoise.transactions import get_connection
from tortoise.utils import get_schema_sql

import dipdup.utils as utils
from dipdup.codegen import DipDupCodeGenerator
from dipdup.config import (
    ROLLBACK_HANDLER,
    BcdDatasourceConfig,
    BigMapIndexConfig,
    CoinbaseDatasourceConfig,
    DatasourceConfigT,
    DipDupConfig,
    IndexConfigTemplateT,
    OperationIndexConfig,
    PostgresDatabaseConfig,
    StaticTemplateConfig,
    TzktDatasourceConfig,
)
from dipdup.context import DipDupContext, RollbackHandlerContext
from dipdup.datasources import DatasourceT
from dipdup.datasources.bcd.datasource import BcdDatasource
from dipdup.datasources.coinbase.datasource import CoinbaseDatasource
from dipdup.datasources.datasource import IndexDatasource
from dipdup.datasources.proxy import DatasourceRequestProxy
from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.exceptions import ConfigurationError
from dipdup.hasura import configure_hasura
from dipdup.index import BigMapIndex, Index, OperationIndex
from dipdup.models import BigMapData, IndexType, OperationData, State
from dipdup.scheduler import add_job, create_scheduler


class IndexDispatcher:
    def __init__(self, ctx: DipDupContext) -> None:
        self._ctx = ctx

        self._logger = logging.getLogger(__name__)
        self._indexes: Dict[str, Index] = {}

    async def add_index(self, index_config: IndexConfigTemplateT) -> None:
        if index_config.name in self._indexes:
            return
        self._logger.info('Adding index `%s` to dispatcher', index_config.name)
        if isinstance(index_config, OperationIndexConfig):
            datasource_name = cast(TzktDatasourceConfig, index_config.datasource).name
            datasource = self._ctx.datasources[datasource_name]
            if not isinstance(datasource, TzktDatasource):
                raise RuntimeError
            operation_index = OperationIndex(self._ctx, index_config, datasource)
            self._indexes[index_config.name] = operation_index
            await datasource.add_index(index_config)

        elif isinstance(index_config, BigMapIndexConfig):
            datasource_name = cast(TzktDatasourceConfig, index_config.datasource).name
            datasource = self._ctx.datasources[datasource_name]
            if not isinstance(datasource, TzktDatasource):
                raise RuntimeError
            big_map_index = BigMapIndex(self._ctx, index_config, datasource)
            self._indexes[index_config.name] = big_map_index
            await datasource.add_index(index_config)

        else:
            raise NotImplementedError

    async def reload_config(self) -> None:
        if not self._ctx.updated:
            return

        self._logger.info('Reloading config')
        self._ctx.config.initialize()

        for index_config in self._ctx.config.indexes.values():
            if isinstance(index_config, StaticTemplateConfig):
                raise RuntimeError
            await self.add_index(index_config)

        self._ctx.reset()

    async def dispatch_operations(self, datasource: TzktDatasource, operations: List[OperationData]) -> None:
        assert len(set(op.level for op in operations)) == 1
        level = operations[0].level
        for index in self._indexes.values():
            if isinstance(index, OperationIndex) and index.datasource == datasource:
                index.push(level, operations)

    async def dispatch_big_maps(self, datasource: TzktDatasource, big_maps: List[BigMapData]) -> None:
        assert len(set(op.level for op in big_maps)) == 1
        level = big_maps[0].level
        for index in self._indexes.values():
            if isinstance(index, BigMapIndex) and index.datasource == datasource:
                index.push(level, big_maps)

    async def _rollback(self, datasource: TzktDatasource, from_level: int, to_level: int) -> None:
        logger = utils.FormattedLogger(ROLLBACK_HANDLER)
        rollback_fn = self._ctx.config.get_rollback_fn()
        ctx = RollbackHandlerContext(
            config=self._ctx.config,
            datasources=self._ctx.datasources,
            logger=logger,
            datasource=datasource,
            from_level=from_level,
            to_level=to_level,
        )
        await rollback_fn(ctx)

    async def run(self, oneshot=False) -> None:
        self._logger.info('Starting index dispatcher')
        for datasource in self._ctx.datasources.values():
            if not isinstance(datasource, IndexDatasource):
                continue
            datasource.on_operations(self.dispatch_operations)
            datasource.on_big_maps(self.dispatch_big_maps)
            datasource.on_rollback(self._rollback)

        self._ctx.commit()

        while True:
            await self.reload_config()

            async with utils.slowdown(1):
                await asyncio.gather(*[index.process() for index in self._indexes.values()])

            # TODO: Continue if new indexes are spawned from origination
            if oneshot:
                break


class DipDup:
    """Main indexer class.

    Spawns datasources, registers indexes, passes handler callbacks to executor"""

    def __init__(self, config: DipDupConfig) -> None:
        self._logger = logging.getLogger(__name__)
        self._config = config
        self._datasources: Dict[str, DatasourceT] = {}
        self._datasources_by_config: Dict[DatasourceConfigT, DatasourceT] = {}
        self._ctx = DipDupContext(
            config=self._config,
            datasources=self._datasources,
        )
        self._index_dispatcher = IndexDispatcher(self._ctx)
        self._scheduler = create_scheduler()

    async def init(self) -> None:
        """Create new or update existing dipdup project"""
        await self._create_datasources()

        codegen = DipDupCodeGenerator(self._config, self._datasources_by_config)
        await codegen.create_package()
        await codegen.fetch_schemas()
        await codegen.generate_types()
        await codegen.generate_default_handlers()
        await codegen.generate_user_handlers()
        await codegen.generate_jobs()
        await codegen.cleanup()

        for datasource in self._datasources.values():
            await datasource.close_session()

    async def run(self, reindex: bool, oneshot: bool) -> None:
        """Main entrypoint"""

        url = self._config.database.connection_string
        models = f'{self._config.package}.models'

        async with utils.tortoise_wrapper(url, models):
            await self._initialize_database(reindex)
            await self._create_datasources()
            await self._configure()

            self._logger.info('Starting datasources')
            datasource_tasks = [] if oneshot else [asyncio.create_task(d.run()) for d in self._datasources.values()]
            worker_tasks = []

            if self._config.hasura:
                worker_tasks.append(asyncio.create_task(configure_hasura(self._config)))

            if self._config.jobs and not oneshot:
                for job_name, job_config in self._config.jobs.items():
                    add_job(self._ctx, self._scheduler, job_name, job_config)
                self._scheduler.start()

            worker_tasks.append(asyncio.create_task(self._index_dispatcher.run(oneshot)))

            try:
                await asyncio.gather(*datasource_tasks, *worker_tasks)
            except KeyboardInterrupt:
                pass
            finally:
                self._logger.info('Closing datasource sessions')
                await asyncio.gather(*[d.close_session() for d in self._datasources.values()])
                # FIXME: AttributeError: 'NoneType' object has no attribute 'call_soon_threadsafe'
                with suppress(AttributeError, SchedulerNotRunningError):
                    self._scheduler.shutdown(wait=True)

    async def migrate_to_v10(self) -> None:
        codegen = DipDupCodeGenerator(self._config, self._datasources_by_config)
        await codegen.generate_default_handlers(recreate=True)
        await codegen.migrate_user_handlers_to_v10()
        self._finish_migration('1.0')

    async def migrate_to_v11(self) -> None:
        codegen = DipDupCodeGenerator(self._config, self._datasources_by_config)
        await codegen.migrate_user_handlers_to_v11()
        self._finish_migration('1.1')

    async def _configure(self) -> None:
        """Run user-defined initial configuration handler"""
        configure_fn = self._config.get_configure_fn()
        await configure_fn(self._ctx)
        self._config.initialize()

    async def _create_datasources(self) -> None:
        datasource: DatasourceT
        for name, datasource_config in self._config.datasources.items():
            if name in self._datasources:
                continue

            cache = self._config.cache_enabled if datasource_config.cache is None else datasource_config.cache
            if isinstance(datasource_config, TzktDatasourceConfig):
                proxy = DatasourceRequestProxy(
                    cache=cache,
                    retry_count=datasource_config.retry_count,
                    retry_sleep=datasource_config.retry_sleep,
                )
                datasource = TzktDatasource(
                    url=datasource_config.url,
                    proxy=proxy,
                )
            elif isinstance(datasource_config, BcdDatasourceConfig):
                proxy = DatasourceRequestProxy(
                    cache=cache,
                    retry_count=datasource_config.retry_count,
                    retry_sleep=datasource_config.retry_sleep,
                )
                datasource = BcdDatasource(
                    url=datasource_config.url,
                    network=datasource_config.network,
                    proxy=proxy,
                )
            elif isinstance(datasource_config, CoinbaseDatasourceConfig):
                proxy = DatasourceRequestProxy(
                    cache=cache,
                    retry_count=datasource_config.retry_count,
                    retry_sleep=datasource_config.retry_sleep,
                    ratelimiter=AsyncLimiter(max_rate=10, time_period=1),
                )
                datasource = CoinbaseDatasource(
                    proxy=proxy,
                )
            else:
                raise NotImplementedError

            self._datasources[name] = datasource
            self._datasources_by_config[datasource_config] = datasource

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

        # TODO: Move higher
        if reindex:
            self._logger.warning('Started with `--reindex` argument, reindexing')
            await self._ctx.reindex()

        try:
            schema_state = await State.get_or_none(index_type=IndexType.schema, index_name=connection_name)
        except OperationalError:
            schema_state = None

        if schema_state is None:
            await Tortoise.generate_schemas()
            await self._execute_sql_scripts(reindex=True)

            schema_state = State(index_type=IndexType.schema, index_name=connection_name, hash=schema_hash)
            await schema_state.save()
        elif schema_state.hash != schema_hash:
            self._logger.warning('Schema hash mismatch, reindexing')
            await self._ctx.reindex()

        await self._execute_sql_scripts(reindex=False)

    async def _execute_sql_scripts(self, reindex: bool) -> None:
        """Execute SQL included with project"""
        sql_path = join(self._config.package_path, 'sql')
        if not exists(sql_path):
            return
        if any(map(lambda p: p not in ('on_reindex', 'on_restart'), listdir(sql_path))):
            raise ConfigurationError(
                f'SQL scripts must be placed either to `{self._config.package}/sql/on_restart` or to `{self._config.package}/sql/on_reindex` directory'
            )
        if not isinstance(self._config.database, PostgresDatabaseConfig):
            self._logger.warning('Execution of user SQL scripts is supported on PostgreSQL only, skipping')
            return

        sql_path = join(sql_path, 'on_reindex' if reindex else 'on_restart')
        if not exists(sql_path):
            return
        self._logger.info('Executing SQL scripts from `%s`', sql_path)
        for filename in sorted(listdir(sql_path)):
            if not filename.endswith('.sql'):
                continue

            with open(join(sql_path, filename)) as file:
                sql = file.read()

            self._logger.info('Executing `%s`', filename)
            await get_connection(None).execute_script(sql)

    def _finish_migration(self, version: str) -> None:
        self._logger.warning('==================== WARNING =====================')
        self._logger.warning('Your project has been migrated to spec version %s.', version)
        self._logger.warning('Review and commit changes before proceeding.')
        self._logger.warning('==================== WARNING =====================')
