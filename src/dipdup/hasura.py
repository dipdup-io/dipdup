import asyncio
from collections import namedtuple
import importlib
import logging
from contextlib import suppress
from typing import Any, Dict, Iterator, List, Tuple, Type

import aiohttp
import humps  # type: ignore
import inflect  # type: ignore
from aiohttp import ClientConnectorError, ClientOSError
from tortoise import Model, fields
from tortoise.transactions import get_connection

from dipdup.config import HasuraConfig, PostgresDatabaseConfig, pascal_to_snake
from dipdup.utils import http_request

inf = inflect.engine()

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
        metadata = await self._generate_metadata()
        existing_metadata = await self._fetch_metadata()

        self._logger.info('Merging existing metadata')
        metadata_tables = [table['table'] for table in metadata['tables']]
        for table in existing_metadata['tables']:
            if table['table'] not in metadata_tables:
                metadata['tables'].append(table)

        await self._replace_metadata(metadata)

        if self._hasura_config.camel_case:
            await self._apply_camelcase()
        
        await self._create_rest_endpoints()

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
        metadata = await self._hasura_http_request(
            endpoint='query',
            json={
                "type": "export_metadata",
                "args": {},
            },
        )
        # TODO: Support multiple sources. Forbidden in config for now.
        return metadata['sources'][0]

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

    async def _generate_metadata(self) -> Dict[str, Any]:
        """Generate metadata based on project models and views.

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
            metadata_tables[view]['select_permissions'].append(self._format_select_permissions())

        for app, model in _iter_models(models, int_models):
            table_name = model_tables[f'{app}.{model.__name__}']

            metadata_tables[table_name]['select_permissions'].append(
                self._format_select_permissions(),
            )

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

        return self._format_metadata(tables=list(metadata_tables.values()))

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
        return [
            Field(name=f['name'], type=f['type']['ofType']['name'])
            for f in fields
            # NOTE: Exclude autogenerated aggregate and pk fields
            if not f['name'].endswith('_aggregate') and not f['name'].endswith('_by_pk')
            # NOTE: Exclude relations. Not reliable enough but ok for now.
            and not (f['description'] or '').endswith('relationship')
        ]

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

    async def _create_rest_endpoints(self) -> None:
        if not self._hasura_config.rest_endpoints:
            return
        queries = []
        for endpoint_name, endpoint_config in self._hasura_config.rest_endpoints.items():
            fields = await self._get_fields(endpoint_config.table)
            queries.append(self._format_rest_query(endpoint_name, endpoint_config.table, fields))
        create_query_collection_request = self._format_create_query_collection(queries)
        await self._hasura_http_request(
            endpoint='query',
            json=create_query_collection_request,
        )
        create_rest_endpoint_request = self._format_create_rest_endpoint(queries)
        await self._hasura_http_request(
            endpoint='query',
            json=create_rest_endpoint_request,
        )

    def _format_rest_query(self, name: str, table: str, fields: List[Field]) -> Dict[str, Any]:
        def _type(type_: str) -> str:
            return type_.replace('bigint', 'Number')

        query_name = humps.camelize(name)
        query_args = ', '.join(f'${f.name}: {_type(f.type)}' for f in fields)
        query_filters = ', '.join(f'{f.name}: ${f.name}' for f in fields)
        query_fields = ' '.join(f.name for f in fields)
        return {
            'name': query_name,
            'query': 'query ' + query_name + ' (' + query_args + ') {' + table + '(' + query_filters + ') {' + query_fields + '}}',
        }

    def _format_create_rest_endpoint_subquery(self, query: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "type": "create_rest_endpoint",
            "args": {
                "name": query['name'],
                "url": query['name'],
                "definition": {
                    "query": {
                        "query_name": query['name'],
                        "collection_name": "allowed-queries",
                    },
                },
                "methods": ["GET"],
            },
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


    def _format_create_rest_endpoint(self, queries: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "type": "bulk",
            "source": "default",
            "args": [self._format_create_rest_endpoint_subquery(q) for q in queries]
        }

    def _format_custom_root_fields(self, table: str) -> Dict[str, Any]:
        words = table.split('_')

        plural = inf.plural_noun(words[-1])
        if plural != False:
            plural_words = words[:-1] + [plural]
        else:
            plural_words = words

        singular = inf.singular_noun(words[-1])
        if singular != False:
            singular_words = words[:-1] + [singular]
        else:
            singular_words = words

        plural_camel = plural_words[0] + ''.join(x.title() for x in plural_words[1:])
        singular_camel = singular_words[0] + ''.join(x.title() for x in singular_words[1:])

        return {
            'select': plural_camel,
            'select_by_pk': singular_camel,
            'select_aggregate': plural_camel + 'Aggregate',
            'insert': plural_camel + 'Insert',
            'insert_one': singular_camel + 'Insert',
            'update': plural_camel + 'Update',
            'update_by_pk': singular_camel + 'Update',
            'delete': plural_camel + 'Delete',
            'delete_by_pk': singular_camel + 'Delete',
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
            "select_permissions": [],
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

    def _format_metadata(self, tables: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "version": 2,
            "tables": tables,
        }
