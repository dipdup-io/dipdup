import asyncio
import importlib
import json
import logging
from contextlib import suppress
from typing import Any, Dict, Iterator, List, Tuple, Type

import aiohttp
from aiohttp import ClientConnectorError, ClientOSError
from tortoise import Model, fields

from dipdup.config import DipDupConfig, PostgresDatabaseConfig, camel_to_snake
from dipdup.exceptions import ConfigurationError
from dipdup.utils import http_request

_logger = logging.getLogger(__name__)


def _is_model_class(obj) -> bool:
    return isinstance(obj, type) and issubclass(obj, Model) and obj != Model


def _format_array_relationship(
    related_name: str,
    table: str,
    column: str,
    schema: str = 'public',
) -> Dict[str, Any]:
    return {
        "name": related_name,
        "using": {
            "foreign_key_constraint_on": {
                "column": column,
                "table": {
                    "schema": schema,
                    "name": table,
                },
            },
        },
    }


def _format_object_relationship(name: str, column: str) -> Dict[str, Any]:
    return {
        "name": name,
        "using": {
            "foreign_key_constraint_on": column,
        },
    }


def _format_select_permissions(columns: List[str]) -> Dict[str, Any]:
    return {
        "role": "user",
        "permission": {
            "columns": sorted(columns),
            "filter": {},
            "allow_aggregations": True,
        },
    }


def _format_table(name: str, schema: str = 'public') -> Dict[str, Any]:
    return {
        "table": {
            "schema": schema,
            "name": name,
        },
        "object_relationships": [],
        "array_relationships": [],
        "select_permissions": [],
    }


def _format_metadata(tables: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "version": 2,
        "tables": tables,
    }


def _iter_models(*modules) -> Iterator[Tuple[str, Type[Model]]]:
    for models in modules:
        for attr in dir(models):
            model = getattr(models, attr)
            if _is_model_class(model):
                app = 'int_models' if models.__name__ == 'dipdup.models' else 'models'
                yield app, model


async def generate_hasura_metadata(config: DipDupConfig) -> Dict[str, Any]:
    _logger.info('Generating Hasura metadata')
    metadata_tables = {}
    model_tables = {}

    int_models = importlib.import_module('dipdup.models')
    models = importlib.import_module(f'{config.package}.models')

    for app, model in _iter_models(models, int_models):
        table_name = model._meta.db_table or camel_to_snake(model.__name__)  # pylint: disable=protected-access
        model_tables[f'{app}.{model.__name__}'] = table_name

        table = _format_table(
            name=table_name,
            schema=config.database.schema_name if isinstance(config.database, PostgresDatabaseConfig) else 'public',
        )
        metadata_tables[table_name] = table

    for app, model in _iter_models(models, int_models):
        table_name = model_tables[f'{app}.{model.__name__}']

        metadata_tables[table_name]['select_permissions'].append(
            _format_select_permissions(list(model._meta.db_fields)),
        )

        for field in model._meta.fields_map.values():
            if isinstance(field, fields.relational.ForeignKeyFieldInstance):
                if not isinstance(field.related_name, str):
                    raise Exception(f'`related_name` of `{field}` must be set')
                related_table_name = model_tables[field.model_name]
                metadata_tables[table_name]['object_relationships'].append(
                    _format_object_relationship(
                        name=field.model_field_name,
                        column=field.model_field_name + '_id',
                    )
                )
                metadata_tables[related_table_name]['array_relationships'].append(
                    _format_array_relationship(
                        related_name=field.related_name,
                        table=table_name,
                        column=field.model_field_name + '_id',
                        schema=config.database.schema_name if isinstance(config.database, PostgresDatabaseConfig) else 'public',
                    )
                )

    return _format_metadata(tables=list(metadata_tables.values()))


async def configure_hasura(config: DipDupConfig):

    if config.hasura is None:
        raise ConfigurationError('`hasura` config section missing')

    _logger.info('Configuring Hasura')

    url = config.hasura.url.rstrip("/")
    hasura_metadata = await generate_hasura_metadata(config)

    _logger.info('Waiting for Hasura instance to be healthy')
    for _ in range(60):
        with suppress(ClientConnectorError, ClientOSError):
            async with aiohttp.ClientSession() as session:
                await session.get(f'{url}/healthz')
                break
        await asyncio.sleep(1)
    else:
        _logger.error('Hasura instance not responding for 60 seconds')
        return

    headers = {}
    if config.hasura.admin_secret:
        headers['X-Hasura-Admin-Secret'] = config.hasura.admin_secret

    _logger.info('Fetching existing metadata')
    existing_hasura_metadata = await http_request(
        'post',
        url=f'{url}/v1/query',
        data=json.dumps(
            {
                "type": "export_metadata",
                "args": hasura_metadata,
            },
        ),
        headers=headers,
    )

    _logger.info('Merging existing metadata')
    hasura_metadata_tables = [table['table'] for table in hasura_metadata['tables']]
    for table in existing_hasura_metadata['tables']:
        if table['table'] not in hasura_metadata_tables:
            hasura_metadata['tables'].append(table)

    _logger.info('Sending replace metadata request')
    result = await http_request(
        'post',
        url=f'{url}/v1/query',
        data=json.dumps(
            {
                "type": "replace_metadata",
                "args": hasura_metadata,
            },
        ),
        headers=headers,
    )
    if not result.get('message') == 'success':
        _logger.error('Can\'t configure Hasura instance: %s', result)
