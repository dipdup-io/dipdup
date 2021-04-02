import asyncio
import logging
import os
from dataclasses import dataclass
from functools import wraps
from os.path import dirname, join

import click
from tortoise import Tortoise

import dipdup.codegen as codegen
from dipdup import __version__
from dipdup.config import DipDupConfig, LoggingConfig
from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.models import State

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
@click.option('--config', '-c', type=str, help='Path to dipdup YAML config')
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

    _config.initialize()

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
        await Tortoise.generate_schemas()

        _logger.info('Fetching indexer state for dapp `%s`', config.package)

        state, _ = await State.get_or_create(dapp=config.package)

        datasources = []

        for index_name, index_config in config.indexes.items():
            _logger.info('Processing index `%s`', index_name)
            if not index_config.operation:
                raise NotImplementedError('Only operation indexes are supported')
            operation_index_config = index_config.operation

            datasource_config = config.datasources[operation_index_config.datasource].tzkt
            _logger.info('Creating datasource `%s`', operation_index_config.datasource)
            datasource = TzktDatasource(datasource_config.url, operation_index_config, state)
            datasources.append(datasource)

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

    codegen.create_package(config)
    codegen.fetch_schemas()
    codegen.generate_types(config)
    codegen.generate_handlers(config)
