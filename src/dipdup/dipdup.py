import asyncio
import hashlib
import logging
import operator
from collections import Counter
from contextlib import AsyncExitStack, asynccontextmanager, suppress
from functools import reduce
from os import listdir
from os.path import join
from typing import Dict, List, Optional, Set, cast

import sqlparse  # type: ignore
from genericpath import exists
from tortoise import Tortoise
from tortoise.exceptions import OperationalError
from tortoise.transactions import get_connection
from tortoise.utils import get_schema_sql

import dipdup.models as models
from dipdup.codegen import DipDupCodeGenerator
from dipdup.config import (
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
from dipdup.context import CallbackManager, DipDupContext
from dipdup.datasources.bcd.datasource import BcdDatasource
from dipdup.datasources.coinbase.datasource import CoinbaseDatasource
from dipdup.datasources.datasource import Datasource, IndexDatasource
from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.exceptions import ConfigurationError, ReindexingRequiredError
from dipdup.hasura import HasuraGateway
from dipdup.index import BigMapIndex, Index, OperationIndex
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
                raise RuntimeError(f'`{datasource_name}` is not a TzktDatasource')
            operation_index = OperationIndex(self._ctx, index_config, datasource)
            self._indexes[index_config.name] = operation_index
            await datasource.add_index(index_config)

        elif isinstance(index_config, BigMapIndexConfig):
            datasource_name = cast(TzktDatasourceConfig, index_config.datasource).name
            datasource = self._ctx.datasources[datasource_name]
            if not isinstance(datasource, TzktDatasource):
                raise RuntimeError(f'`{datasource_name}` is not a TzktDatasource')
            big_map_index = BigMapIndex(self._ctx, index_config, datasource)
            self._indexes[index_config.name] = big_map_index
            await datasource.add_index(index_config)

        else:
            raise NotImplementedError

        for handler_config in index_config.handlers:
            self._ctx.callbacks.register_handler(handler_config)

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

    async def dispatch_big_maps(self, datasource: TzktDatasource, big_maps: List[BigMapData], block: HeadBlockData) -> None:
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
        self._callbacks: CallbackManager = CallbackManager(self._config.package)
        self._ctx = DipDupContext(
            config=self._config,
            datasources=self._datasources,
            callbacks=self._callbacks,
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

        await self._create_datasources(realtime=not oneshot)

        tasks: Set[asyncio.Task] = set()
        async with AsyncExitStack() as stack:
            await self._set_up_database(stack, reindex)
            await self._set_up_datasources(stack, tasks, pre=True)
            await self._set_up_hooks()

            await self._initialize_schema()
            await self._set_up_hasura(stack, tasks)

            if not oneshot:
                await self._set_up_jobs(stack)
                await self._set_up_datasources(stack, tasks, pre=False)

            tasks.add(asyncio.create_task(self._index_dispatcher.run(oneshot)))

            try:
                await asyncio.gather(*tasks)
            except KeyboardInterrupt:
                pass
            except GeneratorExit:
                pass

    async def migrate_to_v10(self) -> None:
        codegen = DipDupCodeGenerator(self._config, self._datasources_by_config)
        self._logger.warning('Not updating default handlers: deprecated in favor of hooks introduced in 1.2 spec')
        self._logger.info('See release notes for more information')
        await codegen.migrate_user_handlers_to_v10()
        self._finish_migration('1.0')

    async def migrate_to_v11(self) -> None:
        codegen = DipDupCodeGenerator(self._config, self._datasources_by_config)
        await codegen.migrate_user_handlers_to_v11()
        self._finish_migration('1.1')

    async def migrate_to_v12(self) -> None:
        codegen = DipDupCodeGenerator(self._config, self._datasources_by_config)
        await codegen.generate_hooks()
        self._finish_migration('1.2')

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

    async def _initialize_schema(self) -> None:
        self._logger.info('Initializing database schema')
        schema_name = 'public'
        connection = next(iter(Tortoise._connections.values()))

        if isinstance(self._config.database, PostgresDatabaseConfig):
            schema_name = self._config.database.schema_name
            await connection.execute_script(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
            await connection.execute_script(f"SET search_path TO {schema_name}")

        try:
            schema_state = await models.Schema.get_or_none(name=schema_name)
        except OperationalError:
            schema_state = None
        # TODO: Fix Tortoise ORM to raise more specific exception
        except KeyError as e:
            raise ReindexingRequiredError(None) from e

        schema_sql = get_schema_sql(connection, False)

        # NOTE: Column order could differ in two generated schemas for the same models, drop commas and sort strings to eliminate this
        # TODO: Ignore comments
        processed_schema_sql = '\n'.join(sorted(schema_sql.replace(',', '').split('\n'))).encode()
        schema_hash = hashlib.sha256(processed_schema_sql).hexdigest()

        # NOTE: `State.config_hash` field contains schema hash when `type` is `IndexType.schema`
        if schema_state is None:
            await Tortoise.generate_schemas()
            # await self._execute_sql_scripts(reindex=True)
            await self._ctx.fire_hook('on_reindex')

            schema_state = models.Schema(
                name=schema_name,
                hash=schema_hash,
            )
            try:
                await schema_state.save()
            except OperationalError as e:
                raise ReindexingRequiredError(None) from e

        elif schema_state.hash != schema_hash:
            self._logger.warning('Schema hash mismatch, reindexing')
            await self._ctx.reindex()

        # await self._execute_sql_scripts(reindex=False)
        await self._ctx.fire_hook('on_restart')

    async def _set_up_database(self, stack: AsyncExitStack, reindex: bool) -> None:
        url = self._config.database.connection_string
        models = f'{self._config.package}.models'
        await stack.enter_async_context(tortoise_wrapper(url, models))

        if reindex:
            self._logger.warning('Started with `--reindex` argument, reindexing')
            await self._ctx.reindex()

    async def _set_up_hooks(self) -> None:
        for hook_config in self._config.hooks.values():
            self._ctx.callbacks.register_hook(hook_config)

    async def _set_up_jobs(self, stack: AsyncExitStack) -> None:
        if not self._config.jobs:
            return

        await stack.enter_async_context(self._scheduler_context())
        for job_config in self._config.jobs.values():
            add_job(self._ctx, self._scheduler, job_config)

    async def _set_up_hasura(self, stack: AsyncExitStack, tasks: Set[asyncio.Task]) -> None:
        if not self._config.hasura:
            return

        if not isinstance(self._config.database, PostgresDatabaseConfig):
            raise RuntimeError
        hasura_gateway = HasuraGateway(self._config.package, self._config.hasura, self._config.database)
        await stack.enter_async_context(hasura_gateway)
        tasks.add(asyncio.create_task(hasura_gateway.configure()))

    async def _set_up_datasources(self, stack: AsyncExitStack, tasks: Set[asyncio.Task], pre: bool) -> None:
        if pre:
            for datasource in self._datasources.values():
                await stack.enter_async_context(datasource)
        else:
            tasks.update(asyncio.create_task(d.run()) for d in self._datasources.values())

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
            for statement in sqlparse.split(sql):
                # NOTE: Ignore empty statements
                with suppress(AttributeError):
                    await get_connection(None).execute_script(statement)

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
