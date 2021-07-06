import asyncio
import importlib
import logging
from collections import namedtuple
from contextlib import suppress
from typing import Any, Dict, Iterator, List, Tuple, Type

import aiohttp
import humps  # type: ignore
from aiohttp import ClientConnectorError, ClientOSError
from tortoise import Model, fields
from tortoise.transactions import get_connection

from dipdup.config import HasuraConfig, PostgresDatabaseConfig, pascal_to_snake
from dipdup.exceptions import ConfigurationError
from dipdup.utils import http_request

Field = namedtuple('Field', ['name', 'type'])


def _is_model_class(obj: Any) -> bool:
    """Is subclass of tortoise.Model, but not the base class"""
    return isinstance(obj, type) and issubclass(obj, Model) and obj != Model and not getattr(obj.Meta, 'abstract', False)


def _iter_models(*modules) -> Iterator[Tuple[str, Type[Model]]]:
    """Iterate over built-in and project's models"""
    for models in modules:
        for attr in dir(models):
            model = getattr(models, attr)
            if _is_model_class(model):
                app = 'int_models' if models.__name__ == 'dipdup.models' else 'models'
                yield app, model


class HasuraError(RuntimeError):
    ...


class HasuraManager:
    def __init__(self, package: str, hasura_config: HasuraConfig, database_config: PostgresDatabaseConfig) -> None:
        self._logger = logging.getLogger(__name__)
        self._package = package
        self._hasura_config = hasura_config
        self._database_config = database_config
        self._session = aiohttp.ClientSession()

    async def configure(self) -> None:
        """Generate Hasura metadata and apply to instance with credentials from `hasura` config section."""

        self._logger.info('Configuring Hasura')
        await self._healthcheck()
        metadata = await self._fetch_metadata()

        self._logger.info('Generating metadata')

        # NOTE: Hasura metadata updated in three steps, order matters:
        # NOTE: 1. Generate and apply tables metadata.
        # FIXME: Existing select permissions are lost
        source_tables_metadata = await self._generate_source_tables_metadata()
        metadata['sources'][0]['tables'] = self._merge_metadata(
            existing=metadata['sources'][0]['tables'],
            generated=source_tables_metadata,
            key=lambda m: m['table']['name'],
        )
        await self._replace_metadata(metadata)

        # NOTE: 2. Apply camelcase and refresh metadata
        if self._hasura_config.camel_case:
            await self._apply_camelcase()
            metadata = await self._fetch_metadata()

        # NOTE: 3. Generate and apply queries and rest endpoints
        query_collections_metadata = await self._generate_query_collections_metadata()
        rest_endpoints_metadata = await self._generate_rest_endpoints_metadata()

        try:
            metadata['query_collections'][0]['definition']['queries'] = self._merge_metadata(
                # TODO: Separate collection?
                existing=metadata['query_collections'][0]['definition']['queries'],
                generated=query_collections_metadata,
                key=lambda m: m['name'],
            )
        except KeyError:
            metadata['query_collections'] = [{"name": "allowed-queries", "definition": {"queries": query_collections_metadata}}]

        metadata['rest_endpoints'] = self._merge_metadata(
            existing=metadata.get('rest_endpoints', []),
            generated=rest_endpoints_metadata,
            key=lambda m: m['name'],
        )

        await self._replace_metadata(metadata)

        self._logger.info('Hasura instance has been configured')

    async def close_session(self) -> None:
        await self._session.close()

    async def _hasura_http_request(self, endpoint: str, json: Dict[str, Any]) -> Dict[str, Any]:
        self._logger.debug('Sending `%s` request: %s', endpoint, json)
        result = await http_request(
            self._session,
            'post',
            url=f'{self._hasura_config.url}/v1/{endpoint}',
            json=json,
            headers=self._hasura_config.headers,
        )
        if 'error' in result:
            raise HasuraError('Can\'t configure Hasura instance', result)
        return result

    async def _healthcheck(self) -> None:
        self._logger.info('Waiting for Hasura instance to be ready')
        for _ in range(self._hasura_config.connection_timeout):
            with suppress(ClientConnectorError, ClientOSError):
                response = await self._session.get(f'{self._hasura_config.url}/healthz')
                if response.status == 200:
                    break
            await asyncio.sleep(1)
        else:
            raise HasuraError(f'Hasura instance not responding for {self._hasura_config.connection_timeout} seconds')

    async def _fetch_metadata(self) -> Dict[str, Any]:
        self._logger.info('Fetching existing metadata')
        return await self._hasura_http_request(
            endpoint='metadata',
            json={
                "type": "export_metadata",
                "args": {},
            },
        )

    async def _replace_metadata(self, metadata: Dict[str, Any]) -> None:
        self._logger.info('Replacing metadata')
        await self._hasura_http_request(
            endpoint='query',
            json={
                "type": "replace_metadata",
                "args": metadata,
            },
        )

    async def _get_views(self) -> List[str]:
        return [
            row[0]
            for row in (
                await get_connection(None).execute_query(
                    f"SELECT table_name FROM information_schema.views WHERE table_schema = '{self._database_config.schema_name}'"
                )
            )[1]
        ]

    async def _generate_source_tables_metadata(self) -> List[Dict[str, Any]]:
        """Generate source tables metadata based on project models and views.

        Includes tables and their relations.
        """

        self._logger.info('Generating Hasura metadata')
        views = await self._get_views()

        metadata_tables = {}
        model_tables = {}

        int_models = importlib.import_module('dipdup.models')
        models = importlib.import_module(f'{self._package}.models')

        for app, model in _iter_models(models, int_models):
            table_name = model._meta.db_table or pascal_to_snake(model.__name__)  # pylint: disable=protected-access
            model_tables[f'{app}.{model.__name__}'] = table_name
            metadata_tables[table_name] = self._format_table(table_name)

        for view in views:
            metadata_tables[view] = self._format_table(view)

        for app, model in _iter_models(models, int_models):
            table_name = model_tables[f'{app}.{model.__name__}']

            for field in model._meta.fields_map.values():
                if isinstance(field, fields.relational.ForeignKeyFieldInstance):
                    if not isinstance(field.related_name, str):
                        raise HasuraError(f'`related_name` of `{field}` must be set')
                    related_table_name = model_tables[field.model_name]
                    metadata_tables[table_name]['object_relationships'].append(
                        self._format_object_relationship(
                            name=field.model_field_name,
                            column=field.model_field_name + '_id',
                        )
                    )
                    metadata_tables[related_table_name]['array_relationships'].append(
                        self._format_array_relationship(
                            related_name=field.related_name,
                            table=table_name,
                            column=field.model_field_name + '_id',
                        )
                    )

        return list(metadata_tables.values())

    async def _generate_query_collections_metadata(self) -> List[Dict[str, Any]]:
        queries = []
        for endpoint_name, endpoint_config in self._hasura_config.rest_endpoints.items():
            if endpoint_config.table and endpoint_config.pk:
                table = f'{self._database_config.schema_name}_{endpoint_config.table}'
                fields = await self._get_fields(table)
                queries.append(self._format_rest_query(endpoint_name, table, endpoint_config.pk, fields))
            elif endpoint_config.query:
                queries.append(dict(name=endpoint_name, query=endpoint_config.query))
            else:
                raise ConfigurationError('Either `table` and `pk` or `query` fields must be specified')
        return queries

    async def _generate_rest_endpoints_metadata(self) -> List[Dict[str, Any]]:
        rest_endpoints = []
        for endpoint_name in self._hasura_config.rest_endpoints.keys():
            rest_endpoints.append(self._format_rest_endpoint(endpoint_name))
        return rest_endpoints

    def _merge_metadata(self, existing: List[Dict[str, Any]], generated: List[Dict[str, Any]], key) -> List[Dict[str, Any]]:
        existing_dict = {key(t): t for t in existing}
        generated_dict = {key(t): t for t in generated}
        return list({**existing_dict, **generated_dict}.values())

    async def _get_fields(self, name: str = 'query_root') -> List[Field]:
        query = (
            '''
            query introspectionQuery {
                __type(name: "'''
            + name
            + '''") {
                    kind
                    name
                    fields {
                        name
                        description
                        type {
                            name
                            kind
                            ofType {
                            name
                            kind
                            }
                        }
                    }
                }
            }
        '''
        )

        result = await http_request(
            self._session,
            'post',
            url=f'{self._hasura_config.url}/v1/graphql',
            json={'query': query},
            headers=self._hasura_config.headers,
        )
        try:
            fields = result['data']['__type']['fields']
        except TypeError as e:
            raise HasuraError(f'Unknown table `{name}`') from e

        result = []
        for field in fields:
            # NOTE: Exclude autogenerated aggregate and pk fields
            if field['name'].endswith('_aggregate') or field['name'].endswith('_by_pk'):
                continue

            # NOTE: Exclude relations. Not reliable enough but ok for now.
            if (field['description'] or '').endswith('relationship'):
                continue

            print(field)
            result.append(Field(name=field['name'], type=field['type']['ofType']['name'] if 'type' in field else None))

        return result

    async def _apply_camelcase(self) -> None:
        """Convert table and column names to camelCase.

        Based on https://github.com/m-rgba/hasura-snake-to-camel
        """

        tables = await self._get_fields()

        for table in tables:
            decamelized_table = humps.decamelize(table.name)

            # NOTE: Skip tables from different schemas
            if not decamelized_table.startswith(self._database_config.schema_name):
                continue

            custom_root_fields = self._format_custom_root_fields(decamelized_table)
            columns = await self._get_fields(table.name)
            custom_column_names = self._format_custom_column_names(columns)
            args: Dict[str, Any] = {
                'table': {
                    # NOTE: Remove schema prefix from table name
                    'name': table.name.replace(self._database_config.schema_name, '')[1:],
                    'schema': self._database_config.schema_name,
                },
                'source': self._hasura_config.source,
                'configuration': {
                    'identifier': custom_root_fields['select_by_pk'],
                    'custom_root_fields': custom_root_fields,
                    'custom_column_names': custom_column_names,
                },
            }

            await self._hasura_http_request(
                endpoint='metadata',
                json={
                    'type': 'pg_set_table_customization',
                    'args': args,
                },
            )

    def _format_rest_query(self, name: str, table: str, pk: str, fields: List[Field]) -> Dict[str, Any]:
        table = humps.camelize(table) if self._hasura_config.camel_case else table
        query_name = humps.camelize(name) if self._hasura_config.camel_case else name
        query_args = ', '.join(f'${f.name}: {f.type}' for f in fields if f.name == pk)
        query_filters = ', '.join('where: {' + f.name + ': {_eq: $' + f.name + '}}' for f in fields if f.name == pk)
        query_fields = ' '.join(f.name for f in fields)
        return {
            'name': query_name,
            'query': 'query ' + query_name + ' (' + query_args + ') {' + table + '(' + query_filters + ') {' + query_fields + '}}',
        }

    def _format_rest_endpoint(self, name: str) -> Dict[str, Any]:
        return {
            "definition": {
                "query": {
                    "collection_name": "allowed-queries",
                    "query_name": name,
                },
            },
            "url": name,
            "methods": ["GET", "POST"],
            "name": name,
            "comment": None,
        }

    def _format_create_query_collection(self, queries: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "type": "bulk",
            "source": "default",
            "args": [
                {
                    "type": "create_query_collection",
                    "args": {
                        "name": "allowed-queries",
                        "definition": {
                            "queries": queries,
                        },
                    },
                },
                {
                    "type": "add_collection_to_allowlist",
                    "args": {"collection": "allowed-queries"},
                },
            ],
        }

    def _format_custom_root_fields(self, table: str) -> Dict[str, Any]:
        # NOTE: Do not change original Hasura format, REST endpoints generation will be broken otherwise
        return {
            'select': humps.camelize(table),
            'select_by_pk': humps.camelize(f'{table}_by_pk'),
            'select_aggregate': humps.camelize(f'{table}_aggregate'),
            'insert': humps.camelize(f'insert_{table}'),
            'insert_one': humps.camelize(f'insert_{table}_one'),
            'update': humps.camelize(f'update_{table}'),
            'update_by_pk': humps.camelize(f'update_{table}_by_pk'),
            'delete': humps.camelize(f'delete_{table}'),
            'delete_by_pk': humps.camelize(f'delete_{table}_by_pk'),
        }

    def _format_custom_column_names(self, fields: List[Field]) -> Dict[str, Any]:
        return {f.name: humps.camelize(f.name) for f in fields}

    def _format_table(self, name: str) -> Dict[str, Any]:
        return {
            "table": {
                "schema": self._database_config.schema_name,
                "name": name,
            },
            "object_relationships": [],
            "array_relationships": [],
            "select_permissions": [
                self._format_select_permissions(),
            ],
        }

    def _format_array_relationship(
        self,
        related_name: str,
        table: str,
        column: str,
    ) -> Dict[str, Any]:
        return {
            "name": related_name if not self._hasura_config.camel_case else humps.camelize(related_name),
            "using": {
                "foreign_key_constraint_on": {
                    "column": column,
                    "table": {
                        "schema": self._database_config.schema_name,
                        "name": table,
                    },
                },
            },
        }

    def _format_object_relationship(self, name: str, column: str) -> Dict[str, Any]:
        return {
            "name": name if not self._hasura_config.camel_case else humps.camelize(name),
            "using": {
                "foreign_key_constraint_on": column,
            },
        }

    def _format_select_permissions(self) -> Dict[str, Any]:
        return {
            "role": "user",
            "permission": {
                "columns": "*",
                "filter": {},
                "allow_aggregations": self._hasura_config.allow_aggregations,
                "limit": self._hasura_config.select_limit,
            },
        }
