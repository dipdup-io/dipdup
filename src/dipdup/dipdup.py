import asyncio
import hashlib
import logging
import operator
from collections import Counter
from contextlib import AsyncExitStack, asynccontextmanager, suppress
from functools import reduce
from os import listdir
from os.path import join
from typing import Dict, List, Optional, cast

from genericpath import exists
from tortoise import Tortoise
from tortoise.exceptions import OperationalError
from tortoise.transactions import get_connection
from tortoise.utils import get_schema_sql

from dipdup.codegen import DipDupCodeGenerator
from dipdup.config import (
    ROLLBACK_HANDLER,
    BcdDatasourceConfig,
    BigMapIndexConfig,
    CoinbaseDatasourceConfig,
    ContractConfig,
    DatasourceConfigT,
    DipDupConfig,
    IndexConfigTemplateT,
    IndexTemplateConfig,
    OperationIndexConfig,
    PostgresDatabaseConfig,
    TzktDatasourceConfig,
)
from dipdup.context import DipDupContext, RollbackHandlerContext
from dipdup.datasources.bcd.datasource import BcdDatasource
from dipdup.datasources.coinbase.datasource import CoinbaseDatasource
from dipdup.datasources.datasource import Datasource, IndexDatasource
from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.exceptions import ConfigurationError, ReindexingRequiredError
from dipdup.hasura import HasuraGateway
from dipdup.index import BigMapIndex, Index, OperationIndex
from dipdup.models import BigMapData, HeadBlockData, IndexType, OperationData, State
from dipdup.utils import FormattedLogger, iter_files, slowdown, tortoise_wrapper

INDEX_DISPATCHER_INTERVAL = 1.0
from dipdup.scheduler import add_job, create_scheduler


class IndexDispatcher:
    def __init__(self, ctx: DipDupContext) -> None:
        self._ctx = ctx

        self._logger = logging.getLogger('dipdup')
        self._indexes: Dict[str, Index] = {}
        self._stopped: bool = False

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
            if isinstance(index_config, IndexTemplateConfig):
                raise RuntimeError('Config is not initialized')
            await self.add_index(index_config)

        self._ctx.reset()

        contracts = [index._config.contracts for index in self._indexes.values() if index._config.contracts]
        if not contracts:
            return

        plain_contracts = reduce(operator.add, contracts)
        duplicate_contracts = [cast(ContractConfig, item).name for item, count in Counter(plain_contracts).items() if count > 1]
        if duplicate_contracts:
            self._logger.warning(
                "The following contracts are used in more than one index: %s. Make sure you know what you're doing.",
                ' '.join(duplicate_contracts),
            )

    async def dispatch_operations(self, datasource: TzktDatasource, operations: List[OperationData], block: HeadBlockData) -> None:
        assert len(set(op.level for op in operations)) == 1
        level = operations[0].level
        for index in self._indexes.values():
            if isinstance(index, OperationIndex) and index.datasource == datasource:
                index.push(level, operations, block)

    async def dispatch_big_maps(self, datasource: TzktDatasource, big_maps: List[BigMapData]) -> None:
        assert len(set(op.level for op in big_maps)) == 1
        level = big_maps[0].level
        for index in self._indexes.values():
            if isinstance(index, BigMapIndex) and index.datasource == datasource:
                index.push(level, big_maps)

    async def _rollback(self, datasource: TzktDatasource, from_level: int, to_level: int) -> None:
        logger = FormattedLogger(ROLLBACK_HANDLER)
        if from_level - to_level == 1:
            # NOTE: Single level rollbacks are processed at Index level.
            # NOTE: Notify all indexes with rolled back datasource to skip next level and just verify it
            for index in self._indexes.values():
                if index.datasource == datasource:
                    # NOTE: Continue to rollback with handler
                    if not isinstance(index, OperationIndex):
                        break
                    await index.single_level_rollback(from_level)
            else:
                return

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

        while not self._stopped:
            await self.reload_config()

            async with slowdown(INDEX_DISPATCHER_INTERVAL):
                await asyncio.gather(*[index.process() for index in self._indexes.values()])

            # TODO: Continue if new indexes are spawned from origination
            if oneshot:
                break

    def stop(self) -> None:
        self._stopped = True


class DipDup:
    """Main indexer class.

    Spawns datasources, registers indexes, passes handler callbacks to executor"""

    def __init__(self, config: DipDupConfig) -> None:
        self._logger = logging.getLogger('dipdup')
        self._config = config
        self._datasources: Dict[str, Datasource] = {}
        self._datasources_by_config: Dict[DatasourceConfigT, Datasource] = {}
        self._ctx = DipDupContext(
            config=self._config,
            datasources=self._datasources,
        )
        self._index_dispatcher = IndexDispatcher(self._ctx)
        self._scheduler = create_scheduler()
        self._codegen = DipDupCodeGenerator(self._config, self._datasources_by_config)

    async def init(self) -> None:
        """Create new or update existing dipdup project"""
        await self._create_datasources()

        async with AsyncExitStack() as stack:
            for datasource in self._datasources.values():
                await stack.enter_async_context(datasource)

            await self._codegen.init()

    async def docker_init(self, image: str, tag: str, env_file: str) -> None:
        await self._codegen.docker_init(image, tag, env_file)

    async def run(self, reindex: bool, oneshot: bool) -> None:
        """Main entrypoint"""

        url = self._config.database.connection_string
        models = f'{self._config.package}.models'

        await self._create_datasources(realtime=not oneshot)

        hasura_gateway: Optional[HasuraGateway]
        if self._config.hasura:
            if not isinstance(self._config.database, PostgresDatabaseConfig):
                raise RuntimeError
            hasura_gateway = HasuraGateway(self._config.package, self._config.hasura, self._config.database)
        else:
            hasura_gateway = None

        async with AsyncExitStack() as stack:
            worker_tasks = []
            await stack.enter_async_context(tortoise_wrapper(url, models))
            for datasource in self._datasources.values():
                await stack.enter_async_context(datasource)
            if hasura_gateway:
                await stack.enter_async_context(hasura_gateway)
                worker_tasks.append(asyncio.create_task(hasura_gateway.configure()))

            await self._initialize_database(reindex)
            await self._configure()

            self._logger.info('Starting datasources')
            datasource_tasks = [] if oneshot else [asyncio.create_task(d.run()) for d in self._datasources.values()]

            if self._config.jobs and not oneshot:
                await stack.enter_async_context(self._scheduler_context())
                for job_name, job_config in self._config.jobs.items():
                    add_job(self._ctx, self._scheduler, job_name, job_config)

            worker_tasks.append(asyncio.create_task(self._index_dispatcher.run(oneshot)))

            try:
                await asyncio.gather(*datasource_tasks, *worker_tasks)
            except KeyboardInterrupt:
                pass
            except GeneratorExit:
                pass

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

    async def _create_datasources(self, realtime: bool = True) -> None:
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

    async def _initialize_database(self, reindex: bool = False) -> None:
        self._logger.info('Initializing database')

        if isinstance(self._config.database, PostgresDatabaseConfig) and self._config.database.schema_name:
            await Tortoise._connections['default'].execute_script(f"CREATE SCHEMA IF NOT EXISTS {self._config.database.schema_name}")
            await Tortoise._connections['default'].execute_script(f"SET search_path TO {self._config.database.schema_name}")

        if reindex:
            self._logger.warning('Started with `--reindex` argument, reindexing')
            await self._ctx.reindex()

        self._logger.info('Checking database schema')
        connection_name, connection = next(iter(Tortoise._connections.items()))

        try:
            schema_state = await State.get_or_none(index_type=IndexType.schema, index_name=connection_name)
        except OperationalError:
            schema_state = None
        # TODO: Process exception in Tortoise
        except KeyError as e:
            raise ReindexingRequiredError(None) from e

        schema_sql = get_schema_sql(connection, False)

        # NOTE: Column order could differ in two generated schemas for the same models, drop commas and sort strings to eliminate this
        processed_schema_sql = '\n'.join(sorted(schema_sql.replace(',', '').split('\n'))).encode()
        schema_hash = hashlib.sha256(processed_schema_sql).hexdigest()

        # NOTE: `State.index_hash` field contains schema hash when `index_type` is `IndexType.schema`
        if schema_state is None:
            await Tortoise.generate_schemas()
            await self._execute_sql_scripts(reindex=True)

            schema_state = State(
                index_type=IndexType.schema,
                index_name=connection_name,
                index_hash=schema_hash,
            )
            await schema_state.save()
        elif schema_state.index_hash != schema_hash:
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
        for file in iter_files(sql_path, '.sql'):
            self._logger.info('Executing `%s`', file.name)
            sql = file.read()
            with suppress(AttributeError):
                await get_connection(None).execute_script(sql)

    def _finish_migration(self, version: str) -> None:
        self._logger.warning('==================== WARNING =====================')
        self._logger.warning('Your project has been migrated to spec version %s.', version)
        self._logger.warning('Review and commit changes before proceeding.')
        self._logger.warning('==================== WARNING =====================')

    @asynccontextmanager
    async def _scheduler_context(self):
        self._scheduler.start()
        try:
            yield
        finally:
            self._scheduler.shutdown()
