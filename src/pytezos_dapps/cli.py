import asyncio
import logging
import os
import shutil
import subprocess
from contextlib import suppress
from functools import wraps
from os.path import dirname, join
from typing import cast

import click
from tortoise import Tortoise

from pytezos_dapps import __version__
from pytezos_dapps.config import LoggingConfig, OperationIndexConfig, PytezosDappConfig
from pytezos_dapps.datasources.tzkt.datasource import TzktDatasource
from pytezos_dapps.models import State

_logger = logging.getLogger(__name__)


def click_async(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        return asyncio.run(fn(*args, **kwargs))

    return wrapper


@click.group()
@click.version_option(__version__)
@click.pass_context
@click_async
async def cli(*_args, **_kwargs):
    pass


@cli.command(help='Run pytezos dapp')
@click.option('--config', '-c', type=str, help='Path to the dapp YAML config', default='config.yml')
@click.option('--logging-config', '-l', type=str, help='Path to the logging YAML config', default='logging.yml')
@click.pass_context
@click_async
async def run(_ctx, config: str, logging_config: str) -> None:
    try:
        path = join(os.getcwd(), logging_config)
        LoggingConfig.load(path).apply()
    except FileNotFoundError:
        path = join(dirname(__file__), 'configs', logging_config)
        LoggingConfig.load(path).apply()

    _logger.info('Loading config')
    try:
        path = join(os.getcwd(), config)
        _config = PytezosDappConfig.load(path)
    except FileNotFoundError:
        path = join(dirname(__file__), 'configs', config)
        _config = PytezosDappConfig.load(path)

    _config.initialize()

    try:
        _logger.info('Initializing database')
        await Tortoise.init(
            db_url=_config.database.connection_string,
            modules={
                'models': [f'{_config.package}.models'],
                'int_models': ['pytezos_dapps.models'],
            },
        )
        await Tortoise.generate_schemas()

        _logger.info('Fetching indexer state for dapp `%s`', _config.package)

        state, _ = await State.get_or_create(dapp=_config.package)

        _logger.info('Creating datasource')
        # FIXME:
        datasource_config = list(_config.datasources.values())[0].tzkt
        index_config = cast(OperationIndexConfig, list(_config.indexes.values())[0].operation)
        datasource = TzktDatasource(datasource_config.url, index_config, state)

        _logger.info('Starting datasource')
        await datasource.start()

    finally:
        await Tortoise.close_connections()


@cli.command(help='Generate types')
@click.option('--path', '-p', type=str, help='Path to the dapp root')
@click.pass_context
@click_async
async def generate_types(ctx, path: str):
    logging.basicConfig()

    # TODO: Fetching schemas from TzKT
    _logger.info('Fetching JSON schemas')
    schemas_dir = join(path, 'schemas')

    _logger.info('Removing existing types')
    types_dir = join(path, 'types')
    with suppress(FileNotFoundError):
        shutil.rmtree(types_dir)
    os.mkdir(types_dir)

    for root, dirs, files in os.walk(schemas_dir):
        for dir in dirs:
            dir_path = join(root.replace(schemas_dir, types_dir), dir)
            os.mkdir(dir_path)
            with open(join(dir_path, '__init__.py'), 'w'):
                pass
        for file in files:
            if not file.endswith('.json'):
                continue
            entrypoint_name = file[:-5]

            input_path = join(root, file)
            output_path = join(root.replace(schemas_dir, types_dir), file.replace('.json', '.py'))
            subprocess.run(
                [
                    'datamodel-codegen',
                    '--input',
                    input_path,
                    '--output',
                    output_path,
                    '--class-name',
                    entrypoint_name,
                    '--disable-timestamp',
                ],
                check=True,
            )


async def purge():
    ...
