import asyncio
import hashlib
import json
import logging
import os
import sys
from dataclasses import dataclass
from functools import wraps
from os.path import dirname, join
from typing import Dict, List, Optional

import aiohttp
import click
from tortoise import Tortoise
from tortoise.exceptions import OperationalError
from tortoise.utils import get_schema_sql

import dipdup.codegen as codegen
from dipdup import __version__
from dipdup.config import DipDupConfig, IndexTemplateConfig, LoggingConfig, OperationIndexConfig, TzktDatasourceConfig
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
                pass
                # FIXME: Hash mismatch every time
                # _logger.warning('Schema hash mismatch, consider reindexing')
                # await Tortoise._drop_databases()
                # os.execl(sys.executable, sys.executable, *sys.argv)

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
        datasource_run_tasks = [asyncio.create_task(d.start()) for d in datasources.values()]
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
    await codegen.cleanup(config)


@cli.command(help='Configure Hasura GraphQL Engine')
@click.option('--url', type=str, help='Hasura GraphQL Engine URL', default='http://127.0.0.1:8080')
@click.option('--admin-secret', type=str, help='Hasura GraphQL Engine admin secret', default=None)
@click.pass_context
@click_async
async def configure_graphql(ctx, url: str, admin_secret: Optional[str]):
    config: DipDupConfig = ctx.obj.config

    url = url.rstrip("/")
    hasura_metadata_path = join(config.package_path, 'hasura_metadata.json')
    with open(hasura_metadata_path) as file:
        hasura_metadata = json.load(file)
    headers = {}
    if admin_secret:
        headers['X-Hasura-Admin-Secret'] = admin_secret
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url=f'{url}/v1/query',
            data=json.dumps(
                {
                    "type": "replace_metadata",
                    "args": hasura_metadata,
                },
            ),
            headers=headers,
        ) as resp:
            result = await resp.json()
            if not result.get('message') == 'success':
                raise Exception(result)
