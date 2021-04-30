import asyncio
import hashlib
import importlib
import logging
from typing import Dict

from tortoise import Tortoise
from tortoise.exceptions import OperationalError
from tortoise.utils import get_schema_sql

import dipdup.codegen as codegen
from dipdup import __version__
from dipdup.config import (
    ROLLBACK_HANDLER,
    DipDupConfig,
    IndexTemplateConfig,
    PostgresDatabaseConfig,
    SqliteDatabaseConfig,
    TzktDatasourceConfig,
)
from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.exceptions import ConfigurationError
from dipdup.hasura import configure_hasura
from dipdup.models import IndexType, State
from dipdup.utils import reindex, tortoise_wrapper


class DipDup:
    def __init__(self, config: DipDupConfig) -> None:
        self._logger = logging.getLogger(__name__)
        self._config = config

    async def init(self) -> None:
        await codegen.create_package(self._config)
        await codegen.fetch_schemas(self._config)
        await codegen.generate_types(self._config)
        await codegen.generate_handlers(self._config)
        await codegen.cleanup(self._config)

    async def run(self) -> None:
        url = self._config.database.connection_string
        cache = isinstance(self._config.database, SqliteDatabaseConfig)
        models = f'{self._config.package}.models'

        try:
            rollback_fn = getattr(importlib.import_module(f'{self._config.package}.handlers.{ROLLBACK_HANDLER}'), ROLLBACK_HANDLER)
        except ModuleNotFoundError as e:
            raise ConfigurationError(f'Package `{self._config.package}` not found. Have you forgot to call `init`?') from e

        async with tortoise_wrapper(url, models):
            await self.initialize_database()

            await self._config.initialize()

            datasources: Dict[TzktDatasourceConfig, TzktDatasource] = {}

            for index_name, index_config in self._config.indexes.items():
                if isinstance(index_config, IndexTemplateConfig):
                    raise RuntimeError('Config is not initialized')

                self._logger.info('Processing index `%s`', index_name)
                if isinstance(index_config.datasource, TzktDatasourceConfig):
                    if index_config.datasource_config not in datasources:
                        datasources[index_config.datasource_config] = TzktDatasource(index_config.datasource_config.url, cache)
                        datasources[index_config.datasource_config].set_rollback_fn(rollback_fn)
                    await datasources[index_config.datasource_config].add_index(index_name, index_config)
                else:
                    raise NotImplementedError(f'Datasource `{index_config.datasource}` is not supported')

            self._logger.info('Starting datasources')
            run_tasks = [asyncio.create_task(d.start()) for d in datasources.values()]

            if self._config.hasura:
                hasura_task = asyncio.create_task(configure_hasura(self._config))
                run_tasks.append(hasura_task)

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
