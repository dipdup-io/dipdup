import asyncio
import importlib
import json
import logging
from contextlib import suppress
from typing import Any, Dict, Iterator, List, Tuple, Type

import aiohttp
from aiohttp import ClientConnectorError, ClientOSError
from tortoise import Model, fields
from tortoise.transactions import get_connection

from dipdup.config import DipDupConfig, HasuraConfig, PostgresDatabaseConfig, pascal_to_snake
from dipdup.exceptions import ConfigurationError
from dipdup.utils import http_request

_logger = logging.getLogger(__name__)


class HasuraError(RuntimeError):
    ...


def _is_model_class(obj) -> bool:
    """Is subclass of tortoise.Model, but not the base class"""
    return isinstance(obj, type) and issubclass(obj, Model) and obj != Model and not getattr(obj.Meta, 'abstract', False)


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


def _format_select_permissions(allow_aggregations: bool, select_limit: int) -> Dict[str, Any]:
    return {
        "role": "user",
        "permission": {
            "columns": "*",
            "filter": {},
            "allow_aggregations": allow_aggregations,
            "limit": select_limit,
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


async def _to_camelcase(session, config: HasuraConfig) -> None:
    import sys

    import requests
    import json
    import pandas as pd
    import humps
    import inflect
    import time


    # Introspect > query_root
    query = '''
        query introspectionQueryRoot {
            __type(name:"query_root") {
                kind
                name
                fields {
                    name
                }
            }
        }
    '''

    result = await http_request(
        session,
        'post',
        url=f'{config.url}/v1/graphql',
        json={'query': query},
        headers=config.headers,
    )

    fields = pd.DataFrame(result['data']['__type']['fields'])

    ## Stripping from the _aggregate field to try and target just new tables and views
    fields = fields[fields['name'].str.endswith('_aggregate')]
    fields['name'] = fields['name'].str.replace('_aggregate', '')

    # Inflect word to plural / singular
    p = inflect.engine()

    for i in fields.index:
        # De-camel any pre-camelized names
        field_decamel = humps.decamelize(fields.at[i,'name'])

        # Split up words to lists
        words = field_decamel.split('_')

        # Plural version - last word plural
        plural = p.plural_noun(words[-1])
        if plural != False:
            plural_words = words[:-1]
            plural_words.append(plural)
        else:
            plural_words = words

        # Singular version - last word singular
        singular = p.singular_noun(words[-1])
        if singular != False:
            singular_words = words[:-1]
            singular_words.append(singular)
        else:
            singular_words = words

        # Camel-ise lists
        plural_camel = plural_words[0] + ''.join(x.title() for x in plural_words[1:])
        singular_camel = singular_words[0] + ''.join(x.title() for x in singular_words[1:])

        # Build Object
        jsondata = {}
        args={}
        configuration={}
        custom_root_fields={}

        # Create Custom Root Field Payload
        jsondata['type'] = 'pg_set_table_customization'
        args['table'] = {'name': fields.at[i,'name'][12:], 'schema': 'hic_et_nunc'}
        args['source'] = config.source
        configuration['identifier'] = singular_camel
        custom_root_fields['select'] = plural_camel
        custom_root_fields['select_by_pk'] = singular_camel
        custom_root_fields['select_aggregate'] = plural_camel + 'Aggregate'
        custom_root_fields['insert'] = plural_camel + 'Insert'
        custom_root_fields['insert_one'] = singular_camel + 'Insert'
        custom_root_fields['update'] = plural_camel + 'Update'
        custom_root_fields['update_by_pk'] = singular_camel + 'Update'
        custom_root_fields['delete'] = plural_camel + 'Delete'
        custom_root_fields['delete_by_pk'] = singular_camel + 'Delete'

        jsondata['args'] = args
        args['configuration'] = configuration
        configuration['custom_root_fields'] = custom_root_fields

        result = await http_request(
            session,
            'post',
            url=f'{config.url}/v1/metadata',
            json=jsondata,
            headers=config.headers,
        )
        print(result)

async def generate_hasura_metadata(config: DipDupConfig, views: List[str]) -> Dict[str, Any]:
    """Generate metadata based on dapp models.

    Includes tables and their relations (but not entities created during execution of snippets from `sql` package directory)
    """
    if not isinstance(config.database, PostgresDatabaseConfig):
        raise RuntimeError
    if not config.hasura:
        raise RuntimeError

    _logger.info('Generating Hasura metadata')
    metadata_tables = {}
    model_tables = {}

    int_models = importlib.import_module('dipdup.models')
    models = importlib.import_module(f'{config.package}.models')

    for app, model in _iter_models(models, int_models):
        table_name = model._meta.db_table or pascal_to_snake(model.__name__)  # pylint: disable=protected-access
        model_tables[f'{app}.{model.__name__}'] = table_name
        metadata_tables[table_name] = _format_table(
            name=table_name,
            schema=config.database.schema_name,
        )

    for view in views:
        metadata_tables[view] = _format_table(
            name=view,
            schema=config.database.schema_name,
        )
        metadata_tables[view]['select_permissions'].append(
            _format_select_permissions(
                config.hasura.allow_aggregations,
                config.hasura.select_limit,
            ),
        )

    for app, model in _iter_models(models, int_models):
        table_name = model_tables[f'{app}.{model.__name__}']

        metadata_tables[table_name]['select_permissions'].append(
            _format_select_permissions(
                config.hasura.allow_aggregations,
                config.hasura.select_limit,
            ),
        )

        for field in model._meta.fields_map.values():
            if isinstance(field, fields.relational.ForeignKeyFieldInstance):
                if not isinstance(field.related_name, str):
                    raise HasuraError(f'`related_name` of `{field}` must be set')
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
                        schema=config.database.schema_name,
                    )
                )

    return _format_metadata(tables=list(metadata_tables.values()))


async def configure_hasura(config: DipDupConfig):
    """Generate Hasura metadata and apply to instance with credentials from `hasura` config section."""

    if config.hasura is None:
        raise ConfigurationError('`hasura` config section missing')
    if not isinstance(config.database, PostgresDatabaseConfig):
        raise RuntimeError

    _logger.info('Configuring Hasura')
    views = [
        row[0]
        for row in (
            await get_connection(None).execute_query(
                f"SELECT table_name FROM information_schema.views WHERE table_schema = '{config.database.schema_name}'"
            )
        )[1]
    ]

    hasura_metadata = await generate_hasura_metadata(config, views)

    async with aiohttp.ClientSession() as session:
        _logger.info('Waiting for Hasura instance to be healthy')
        for _ in range(60):
            with suppress(ClientConnectorError, ClientOSError):
                response = await session.get(f'{config.hasura.url}/healthz')
                if response.status == 200:
                    break
            await asyncio.sleep(1)
        else:
            raise HasuraError('Hasura instance not responding for 60 seconds')

        _logger.info('Fetching existing metadata')
        existing_hasura_metadata = await http_request(
            session,
            'post',
            url=f'{config.hasura.url}/v1/query',
            data=json.dumps(
                {
                    "type": "export_metadata",
                    "args": {},
                },
            ),
            headers=config.hasura.headers,
        )
        # FIXME: Not cool
        existing_hasura_metadata = existing_hasura_metadata['sources'][0]

        _logger.info('Merging existing metadata')
        hasura_metadata_tables = [table['table'] for table in hasura_metadata['tables']]
        for table in existing_hasura_metadata['tables']:
            if table['table'] not in hasura_metadata_tables:
                hasura_metadata['tables'].append(table)

        _logger.info('Sending replace metadata request')
        result = await http_request(
            session,
            'post',
            url=f'{config.hasura.url}/v1/query',
            data=json.dumps(
                {
                    "type": "replace_metadata",
                    "args": hasura_metadata,
                },
            ),
            headers=config.hasura.headers,
        )
        if result.get('message') != 'success':
            raise HasuraError('Can\'t configure Hasura instance', result)

        if config.hasura.camelcase:
            await _to_camelcase(session, config.hasura)

        _logger.info('Hasura instance has been configured')
