import asyncio
import hashlib
import logging
import os
import sys
from dataclasses import dataclass
from functools import wraps
from os.path import dirname, join
from typing import Dict, List

import click
from tortoise import Tortoise
from tortoise.exceptions import OperationalError
from tortoise.utils import get_schema_sql

import dipdup.codegen as codegen
from dipdup import __version__
from dipdup.config import DipDupConfig, LoggingConfig, OperationIndexConfig
from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.models import IndexType, State

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

    try:
        _logger.info('Initializing database')
        await Tortoise.init(
            db_url=config.database.connection_string,
            modules={
                'models': [f'{config.package}.models'],
                'int_models': ['dipdup.models'],
            },
        )

        for connection_name, connection in Tortoise._connections.items():
            schema_sql = get_schema_sql(connection, False)
            schema_hash = hashlib.sha256(schema_sql.encode()).hexdigest()

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
                await Tortoise._drop_databases()
                os.execl(sys.executable, sys.executable, *sys.argv)

        await config.initialize()

        _logger.info('Fetching indexer state for dapp `%s`', config.package)

        datasource_operation_index_configs: Dict[str, List[OperationIndexConfig]] = {
            datasource_name: [] for datasource_name in config.datasources
        }
        datasources = []

        for index_name, index_config in config.indexes.items():
            _logger.info('Processing index `%s`', index_name)
            if not index_config.operation:
                raise NotImplementedError('Only operation indexes are supported')
            operation_index_config = index_config.operation
            datasource_operation_index_configs[operation_index_config.datasource].append(operation_index_config)

        for datasource_name, operation_index_configs in datasource_operation_index_configs.items():
            if not operation_index_configs:
                continue

            _logger.info('Creating datasource `%s`', datasource_name)
            if len(operation_index_configs) > 1:
                _logger.warning('Using more than one operation index. Be careful, indexing is not atomic.')

            datasource_config = config.datasources[datasource_name]
            if datasource_config.tzkt:
                datasource = TzktDatasource(
                    url=datasource_config.tzkt.url,
                    operation_index_configs=operation_index_configs,
                )
                datasources.append(datasource)
            else:
                raise NotImplementedError

        _logger.info('Starting datasources')
        datasource_run_tasks = [asyncio.create_task(d.start()) for d in datasources]
        await asyncio.gather(*datasource_run_tasks)

    finally:
        await Tortoise.close_connections()


@cli.command(help='Initialize new dipdap')
@click.pass_context
@click_async
async def init(ctx):
    config: DipDupConfig = ctx.obj.config

    await codegen.create_package(config)
    await codegen.fetch_schemas(config)
    await codegen.generate_types(config)
    await codegen.generate_handlers(config)
    await codegen.generate_hasura_metadata(config)
