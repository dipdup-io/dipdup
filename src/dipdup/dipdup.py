import logging
from asyncio import CancelledError, Task, create_task, gather
from contextlib import AsyncExitStack, asynccontextmanager, suppress
from typing import Dict, List, Set, Union, cast

from tortoise import Tortoise
from tortoise.exceptions import OperationalError
from tortoise.transactions import get_connection

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
from dipdup.exceptions import ConfigInitializationException, ReindexingRequiredError
from dipdup.hasura import HasuraGateway
from dipdup.index import BigMapIndex, Index, OperationIndex
from dipdup.models import BigMapData, Contract, HeadBlockData
from dipdup.models import Index as IndexState
from dipdup.models import OperationData, Schema
from dipdup.scheduler import add_job, create_scheduler
from dipdup.utils import FormattedLogger, slowdown
from dipdup.utils.database import get_schema_hash, set_schema, tortoise_wrapper, validate_models


class IndexDispatcher:
    def __init__(self, ctx: DipDupContext) -> None:
        self._ctx = ctx

        self._logger = logging.getLogger('dipdup')
        self._indexes: Dict[str, Index] = {}
        self._contracts: Set[ContractConfig] = set()
        self._stopped: bool = False

    async def run(self, oneshot=False) -> None:
        self._logger.info('Starting index dispatcher')
        await self._subscribe()
        await self._load_index_states()

        while not self._stopped:
            await self.reload_config()

            async with slowdown(1.0):
                await gather(*[index.process() for index in self._indexes.values()])

            # TODO: Continue if new indexes are spawned from origination
            if oneshot:
                break

    def stop(self) -> None:
        self._stopped = True

    async def add_index(self, index_config: IndexConfigTemplateT) -> None:
        if index_config.name in self._indexes:
            return
        self._logger.info('Adding index `%s` to dispatcher', index_config.name)

        index: Union[OperationIndex, BigMapIndex]
        datasource_name = cast(TzktDatasourceConfig, index_config.datasource).name
        datasource = self._ctx.datasources[datasource_name]
        if not isinstance(datasource, TzktDatasource):
            raise RuntimeError(f'`{datasource_name}` is not a TzktDatasource')

        if isinstance(index_config, OperationIndexConfig):
            index = OperationIndex(self._ctx, index_config, datasource)
        elif isinstance(index_config, BigMapIndexConfig):
            index = BigMapIndex(self._ctx, index_config, datasource)
        else:
            raise NotImplementedError

        self._indexes[index_config.name] = index
        await datasource.add_index(index_config)

        for handler_config in index_config.handlers:
            self._ctx.callbacks.register_handler(handler_config)

        await index.initialize_state()

    async def add_contract(self, contract_config: ContractConfig) -> None:
        if contract_config in self._contracts:
            return

        self._contracts.add(contract_config)
        with suppress(OperationalError):
            await Contract(
                name=contract_config.name,
                address=contract_config.address,
                typename=contract_config.typename,
            ).save()

    async def reload_config(self) -> None:
        if not self._ctx.updated:
            return

        self._logger.info('Config has been updated, reloading')
        if not self._contracts:
            await self._fetch_contracts()

        self._ctx.config.initialize()

        for index_config in self._ctx.config.indexes.values():
            if isinstance(index_config, IndexTemplateConfig):
                raise ConfigInitializationException
            await self.add_index(index_config)

        for contract_config in self._ctx.config.contracts.values():
            await self.add_contract(contract_config)

        self._ctx.reset()

    async def _fetch_contracts(self) -> None:
        contracts = await Contract.filter().all()
        self._logger.info('%s contracts fetched from database', len(contracts))

        for contract in contracts:
            if contract.name not in self._ctx.config.contracts:
                contract_config = ContractConfig(address=contract.address, typename=contract.typename)
                self._ctx.config.contracts[contract.name] = contract_config

    async def _subscribe(self) -> None:
        for datasource in self._ctx.datasources.values():
            if not isinstance(datasource, IndexDatasource):
                continue
            datasource.on_operations(self._dispatch_operations)
            datasource.on_big_maps(self._dispatch_big_maps)
            datasource.on_rollback(self._rollback)

    async def _load_index_states(self) -> None:
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
                    await self._ctx.reindex('config has been modified')

            elif template:
                if template not in self._ctx.config.templates:
                    await self._ctx.reindex(f'template `{template}` has been removed from config')
                self._ctx.add_index(name, template, template_values)

            else:
                self._logger.warning('Index `%s` was removed from config, ignoring', name)

        self._ctx.commit()

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
        self._index_dispatcher = IndexDispatcher(self._ctx)
        self._scheduler = create_scheduler()
        self._codegen = DipDupCodeGenerator(self._config, self._datasources_by_config)

    async def init(self, full: bool = True) -> None:
        """Create new or update existing dipdup project"""
        await self._create_datasources()

        async with AsyncExitStack() as stack:
            for datasource in self._datasources.values():
                await stack.enter_async_context(datasource)

            await self._codegen.init(full)

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
                await self._set_up_jobs(stack)
                await self._spawn_datasources(tasks)

            tasks.add(create_task(self._index_dispatcher.run(oneshot)))

            await gather(*tasks)

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
            schema_state = await Schema.get_or_none(name=schema_name)
        except OperationalError:
            schema_state = None
        # TODO: Fix Tortoise ORM to raise more specific exception
        except KeyError as e:
            raise ReindexingRequiredError from e

        schema_hash = get_schema_hash(conn)

        # NOTE: `State.config_hash` field contains schema hash when `type` is `IndexType.schema`
        if schema_state is None:
            await Tortoise.generate_schemas()
            await self._ctx.fire_hook('on_reindex')

            schema_state = Schema(
                name=schema_name,
                hash=schema_hash,
            )
            try:
                await schema_state.save()
            except OperationalError as e:
                raise ReindexingRequiredError from e

        elif schema_state.hash != schema_hash:
            self._logger.warning('Schema hash mismatch, reindexing')
            await self._ctx.reindex()

        await self._ctx.fire_hook('on_restart')

    async def _set_up_database(self, stack: AsyncExitStack, reindex: bool) -> None:
        validate_models(self._config.package)

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

    async def _spawn_datasources(self, tasks: Set[Task]) -> None:
        tasks.update(create_task(d.run()) for d in self._datasources.values())

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
