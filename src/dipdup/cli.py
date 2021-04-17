import asyncio
import hashlib
import logging
import os
import sys
from dataclasses import dataclass
from functools import wraps
from os.path import dirname, join
from typing import Dict

import click
from tortoise import Tortoise
from tortoise.exceptions import OperationalError
from tortoise.utils import get_schema_sql

import dipdup.codegen as codegen
from dipdup import __version__
from dipdup.config import DipDupConfig, IndexTemplateConfig, LoggingConfig, PostgresDatabaseConfig, TzktDatasourceConfig
from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.hasura import configure_hasura
from dipdup.models import IndexType, State
from dipdup.utils import reindex, tortoise_wrapper

_logger = logging.getLogger(__name__)


def click_async(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        return asyncio.run(fn(*args, **kwargs))

    return wrapper


@dataclass
class CLIContext:
    config: DipDupConfig
    logging_config: LoggingConfig


@click.group()
@click.version_option(__version__)
@click.option('--config', '-c', type=str, help='Path to dipdup YAML config', default='dipdup.yml')
@click.option('--logging-config', '-l', type=str, help='Path to logging YAML config', default='logging.yml')
@click.pass_context
@click_async
async def cli(ctx, config: str, logging_config: str):
    try:
        path = join(os.getcwd(), logging_config)
        _logging_config = LoggingConfig.load(path)
    except FileNotFoundError:
        path = join(dirname(__file__), 'configs', logging_config)
        _logging_config = LoggingConfig.load(path)

    _logging_config.apply()

    _logger.info('Loading config')
    _config = DipDupConfig.load(config)

    ctx.obj = CLIContext(
        config=_config,
        logging_config=_logging_config,
    )


@cli.command(help='Run dipdap')
@click.pass_context
@click_async
async def run(ctx) -> None:
    config: DipDupConfig = ctx.obj.config

    url = config.database.connection_string
    models = f'{config.package}.models'
    async with tortoise_wrapper(url, models):
        _logger.info('Initializing database')

        connection_name, connection = next(iter(Tortoise._connections.items()))
        schema_sql = get_schema_sql(connection, False)

        if isinstance(config.database, PostgresDatabaseConfig) and config.database.schema_name:
            await Tortoise._connections['default'].execute_script("CREATE SCHEMA IF NOT EXISTS {}".format(config.database.schema_name))
            await Tortoise._connections['default'].execute_script("SET search_path TO {}".format(config.database.schema_name))

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
            _logger.warning('Schema hash mismatch, reindexing')
            await reindex()

        await config.initialize()

        _logger.info('Fetching indexer state for dapp `%s`', config.package)
        datasources: Dict[TzktDatasourceConfig, TzktDatasource] = {}

        for index_name, index_config in config.indexes.items():
            assert not isinstance(index_config, IndexTemplateConfig)
            _logger.info('Processing index `%s`', index_name)
            if isinstance(index_config.datasource, TzktDatasourceConfig):
                if index_config.tzkt_config not in datasources:
                    datasources[index_config.tzkt_config] = TzktDatasource(index_config.tzkt_config.url)
                datasources[index_config.tzkt_config].add_index(index_config)
            else:
                raise NotImplementedError(f'Datasource `{index_config.datasource}` is not supported')

        _logger.info('Starting datasources')
        run_tasks = [asyncio.create_task(d.start()) for d in datasources.values()]

        if config.hasura:
            hasura_task = asyncio.create_task(configure_hasura(config))
            run_tasks.append(hasura_task)

        await asyncio.gather(*run_tasks)


@cli.command(help='Initialize new dipdap')
@click.pass_context
@click_async
async def init(ctx):
    config: DipDupConfig = ctx.obj.config

    await codegen.create_package(config)
    await codegen.fetch_schemas(config)
    await codegen.generate_types(config)
    await codegen.generate_handlers(config)
    await codegen.cleanup(config)
