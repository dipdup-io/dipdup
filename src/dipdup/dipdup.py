import asyncio
import hashlib
import importlib
import logging
from copy import copy
from os.path import join
from posix import listdir
from typing import Dict, List, cast

from genericpath import exists
from tortoise import Tortoise
from tortoise.exceptions import OperationalError
from tortoise.transactions import in_transaction
from tortoise.utils import get_schema_sql

import dipdup.codegen as codegen
from dipdup import __version__
from dipdup.config import (
    ROLLBACK_HANDLER,
    BcdDatasourceConfig,
    ContractConfig,
    DatasourceConfigT,
    DipDupConfig,
    DynamicTemplateConfig,
    IndexConfigTemplateT,
    PostgresDatabaseConfig,
    SqliteDatabaseConfig,
    StaticTemplateConfig,
    TzktDatasourceConfig,
)
from dipdup.datasources import DatasourceT
from dipdup.datasources.bcd.datasource import BcdDatasource
from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.exceptions import ConfigurationError
from dipdup.hasura import configure_hasura
from dipdup.models import IndexType, State
from dipdup.utils import reindex, tortoise_wrapper


class DipDup:
    def __init__(self, config: DipDupConfig) -> None:
        self._logger = logging.getLogger(__name__)
        self._config = config
        self._datasources: Dict[str, DatasourceT] = {}
        self._datasources_by_config: Dict[DatasourceConfigT, DatasourceT] = {}
        self._spawned_indexes: List[str] = []

    async def init(self) -> None:
        await codegen.create_package(self._config)
        await codegen.resolve_dynamic_templates(self._config)
        await codegen.fetch_schemas(self._config)
        await codegen.generate_types(self._config)
        await codegen.generate_handlers(self._config)
        await codegen.cleanup(self._config)

    async def configure(self, runtime=False) -> None:
        if not self._datasources:
            raise RuntimeError('Call `create_datasources` first')

        config_module = importlib.import_module(f'{self._config.package}.config')
        config_handler = getattr(config_module, 'configure')
        await config_handler(self._config, self._datasources)

        self._config.pre_initialize()
        await self._config.initialize()

        await self.spawn_indexes(runtime)

    async def create_datasources(self) -> None:
        datasource: DatasourceT
        for name, datasource_config in self._config.datasources.items():
            if name in self._datasources:
                continue

            if isinstance(datasource_config, TzktDatasourceConfig):
                datasource = TzktDatasource(datasource_config.url, self._config.tzkt_cache)

                # FIXME: Reverse dependencies, dirty
                try:
                    rollback_fn = getattr(importlib.import_module(f'{self._config.package}.handlers.{ROLLBACK_HANDLER}'), ROLLBACK_HANDLER)
                except ModuleNotFoundError as e:
                    raise ConfigurationError(f'Package `{self._config.package}` not found. Have you forgot to call `init`?') from e

                datasource.set_rollback_fn(rollback_fn)
                datasource.set_package(self._config.package)

                self._datasources[name] = datasource
                self._datasources_by_config[datasource_config] = datasource

            elif isinstance(datasource_config, BcdDatasourceConfig):
                datasource = BcdDatasource(datasource_config.url, datasource_config.network, self._config.tzkt_cache)

                self._datasources[name] = datasource
                self._datasources_by_config[datasource_config] = datasource
            else:
                raise NotImplementedError

    async def resolve_dynamic_templates(self):
        if not self._datasources:
            raise RuntimeError('Call `create_datasources` first')

        for index_name, index_config in copy(self._config.indexes).items():
            if isinstance(index_config, DynamicTemplateConfig):
                if not self._config.templates:
                    raise ConfigurationError('`templates` section is missing')

                template = self._config.templates[index_config.template]
                # NOTE: Datasource and other fields are str as we haven't initialized DynamicTemplateConfigs yet
                datasource = self._datasources[cast(str, template.datasource)]
                if not isinstance(datasource, TzktDatasource):
                    raise ConfigurationError('Dynamic ')

                contract_config = self._config.contracts[cast(str, index_config.similar_to)]
                await datasource.add_contract_subscription(contract_config, index_name, template, index_config.strict)
                similar_contracts = await self._datasources[template.datasource].get_similar_contracts(contract_config.address)
                for contract_address in similar_contracts:
                    self._config.contracts[contract_address] = ContractConfig(
                        address=contract_address,
                        typename=contract_config.typename,
                    )

                    generated_index_name = f'{index_name}_{contract_address}'
                    template_config = StaticTemplateConfig(template=index_config.template, values=dict(contract=contract_address))
                    self._config.indexes[generated_index_name] = template_config

                del self._config.indexes[index_name]

    async def spawn_indexes(self, runtime=False) -> None:
        resync_datasources = []
        for index_name, index_config in self._config.indexes.items():
            if index_name in self._spawned_indexes:
                continue
            if isinstance(index_config, StaticTemplateConfig):
                raise RuntimeError('Config is not pre-initialized')
            if isinstance(index_config, DynamicTemplateConfig):
                raise RuntimeError('Call `resolve_dynamic_templates` first')

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

    async def configuration_loop(self, interval: int):
        while True:
            await asyncio.sleep(interval)
            await self.configure(runtime=True)

    async def run(self) -> None:
        url = self._config.database.connection_string
        models = f'{self._config.package}.models'

        async with tortoise_wrapper(url, models):
            await self.initialize_database()
            await self.create_datasources()

            if self._config.configuration:
                await self.configure()

            await self.resolve_dynamic_templates()

            # NOTE: We need to initialize config one more time to process generated indexes
            self._config.pre_initialize()
            await self._config.initialize()

            await self.spawn_indexes()

            self._logger.info('Starting datasources')
            run_tasks = [asyncio.create_task(d.run()) for d in self._datasources.values()]

            if self._config.hasura:
                hasura_task = asyncio.create_task(configure_hasura(self._config))
                run_tasks.append(hasura_task)

            if self._config.configuration:
                configuration_task = asyncio.create_task(self.configuration_loop(self._config.configuration.interval))
                run_tasks.append(configuration_task)

            await asyncio.gather(*run_tasks)

    async def initialize_database(self) -> None:
        self._logger.info('Initializing database')

        if isinstance(self._config.database, PostgresDatabaseConfig) and self._config.database.schema_name:
            await Tortoise._connections['default'].execute_script(f"CREATE SCHEMA IF NOT EXISTS {self._config.database.schema_name}")
            await Tortoise._connections['default'].execute_script(f"SET search_path TO {self._config.database.schema_name}")

        connection_name, connection = next(iter(Tortoise._connections.items()))
        schema_sql = get_schema_sql(connection, False)

        # NOTE: Column order could differ in two generated schemas for the same models, drop commas and sort strings to eliminate this
        processed_schema_sql = '\n'.join(sorted(schema_sql.replace(',', '').split('\n'))).encode()
        schema_hash = hashlib.sha256(processed_schema_sql).hexdigest()

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
            await reindex()

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
