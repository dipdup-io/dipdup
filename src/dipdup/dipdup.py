import asyncio
import hashlib
import logging
from functools import partial
from os.path import join
from posix import listdir
from typing import Dict, List, cast

from genericpath import exists
from tortoise import Tortoise
from tortoise.exceptions import OperationalError
from tortoise.transactions import in_transaction
from tortoise.utils import get_schema_sql

import dipdup.utils as utils
from dipdup.codegen import DipDupCodeGenerator
from dipdup.config import (
    ROLLBACK_HANDLER,
    BcdDatasourceConfig,
    BigMapIndexConfig,
    DatasourceConfigT,
    DipDupConfig,
    IndexConfigTemplateT,
    OperationIndexConfig,
    PostgresDatabaseConfig,
    StaticTemplateConfig,
    TzktDatasourceConfig,
)
from dipdup.context import RollbackHandlerContext
from dipdup.datasources import DatasourceT
from dipdup.datasources.bcd.datasource import BcdDatasource
from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.exceptions import HandlerImportError
from dipdup.hasura import configure_hasura
from dipdup.index import BigMapIndex, HandlerContext, Index, OperationIndex
from dipdup.models import BigMapData, IndexType, OperationData, State


class IndexDispatcher:
    def __init__(self, ctx: HandlerContext) -> None:
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

    async def dispatch_operations(self, operations: List[OperationData]) -> None:
        assert len(set(op.level for op in operations)) == 1
        level = operations[0].level
        for index in self._indexes.values():
            if isinstance(index, OperationIndex):
                index.push(level, operations)

    async def dispatch_big_maps(self, big_maps: List[BigMapData]) -> None:
        assert len(set(op.level for op in big_maps)) == 1
        level = big_maps[0].level
        for index in self._indexes.values():
            if isinstance(index, BigMapIndex):
                index.push(level, big_maps)

    async def _rollback(self, datasource: str, from_level: int, to_level: int) -> None:
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
        for name, datasource in self._ctx.datasources.items():
            if not isinstance(datasource, TzktDatasource):
                continue
            datasource.on('operations', self.dispatch_operations)
            datasource.on('big_maps', self.dispatch_big_maps)
            datasource.on('rollback', partial(self._rollback, datasource=name))

        self._ctx.commit()

        while True:
            await self.reload_config()

            # FIXME: Process all indexes in parallel, blocked by https://github.com/tortoise/tortoise-orm/issues/792
            async with utils.slowdown(1):
                for index in self._indexes.values():
                    await index.process()

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
        self._ctx = HandlerContext(
            config=self._config,
            datasources=self._datasources,
            logger=utils.FormattedLogger(__name__),
            template_values=None,
        )
        self._index_dispatcher = IndexDispatcher(self._ctx)

    async def init(self) -> None:
        """Create new or update existing dipdup project"""
        await self._create_datasources()

        codegen = DipDupCodeGenerator(self._config, self._datasources_by_config)
        await codegen.create_package()
        await codegen.fetch_schemas()
        await codegen.generate_types()
        await codegen.generate_default_handlers()
        await codegen.generate_user_handlers()
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

            worker_tasks.append(asyncio.create_task(self._index_dispatcher.run(oneshot)))

            try:
                await asyncio.gather(*datasource_tasks, *worker_tasks)
            except KeyboardInterrupt:
                pass

            self._logger.info('Closing datasource sessions')
            await asyncio.gather(*[d.close_session() for d in self._datasources.values()])

    async def migrate(self) -> None:
        codegen = DipDupCodeGenerator(self._config, self._datasources_by_config)
        await codegen.generate_default_handlers(recreate=True)
        await codegen.migrate_user_handlers_to_v1()
        self._logger.warning('==================== WARNING =====================')
        self._logger.warning('Your handlers have just been migrated to v1.0.0 format.')
        self._logger.warning('Review and commit changes before proceeding.')
        self._logger.warning('==================== WARNING =====================')
        quit()

    async def _configure(self) -> None:
        """Run user-defined initial configuration handler"""
        try:
            configure_fn = self._config.get_configure_fn()
        except HandlerImportError:
            await self.migrate()
        await configure_fn(self._ctx)
        self._config.initialize()

    async def _create_datasources(self) -> None:
        datasource: DatasourceT
        for name, datasource_config in self._config.datasources.items():
            if name in self._datasources:
                continue

            if isinstance(datasource_config, TzktDatasourceConfig):
                datasource = TzktDatasource(
                    url=datasource_config.url,
                    cache=self._config.cache_enabled,
                )
                self._datasources[name] = datasource
                self._datasources_by_config[datasource_config] = datasource

            elif isinstance(datasource_config, BcdDatasourceConfig):
                datasource = BcdDatasource(
                    datasource_config.url,
                    datasource_config.network,
                    self._config.cache_enabled,
                )
                self._datasources[name] = datasource
                self._datasources_by_config[datasource_config] = datasource
            else:
                raise NotImplementedError

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
