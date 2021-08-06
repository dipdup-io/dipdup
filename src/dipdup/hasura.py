import asyncio
import importlib
import logging
import re
from contextlib import suppress
from os.path import dirname, join
from typing import Any, Dict, Iterator, List, Optional, Tuple

import humps  # type: ignore
from aiohttp import ClientConnectorError, ClientOSError
from pydantic.dataclasses import dataclass
from tortoise import fields
from tortoise.transactions import get_connection

from dipdup.config import HasuraConfig, HTTPConfig, PostgresDatabaseConfig, pascal_to_snake
from dipdup.exceptions import ConfigurationError
from dipdup.http import HTTPGateway
from dipdup.utils import iter_files, iter_models

_get_fields_query = '''
query introspectionQuery($name: String!) {
  __type(name: $name) {
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
'''.replace(
    '\n', ' '
).replace(
    '  ', ''
)


@dataclass
class Field:
    name: str
    type: Optional[str]

    def camelize(self) -> 'Field':
        return Field(
            name=humps.camelize(self.name),
            type=self.type,
        )


class HasuraError(RuntimeError):
    ...


class HasuraGateway(HTTPGateway):
    def __init__(
        self,
        package: str,
        hasura_config: HasuraConfig,
        database_config: PostgresDatabaseConfig,
        http_config: Optional[HTTPConfig] = None,
    ) -> None:
        super().__init__(hasura_config.url, http_config)
        self._logger = logging.getLogger('dipdup.hasura')
        self._package = package
        self._hasura_config = hasura_config
        self._database_config = database_config

    async def configure(self, reset: bool = False) -> None:
        """Generate Hasura metadata and apply to instance with credentials from `hasura` config section."""

        self._logger.info('Configuring Hasura')
        await self._healthcheck()

        if reset:
            await self._reset_metadata()

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
        try:
            metadata['query_collections'][0]['definition']['queries'] = self._merge_metadata(
                # TODO: Separate collection?
                existing=metadata['query_collections'][0]['definition']['queries'],
                generated=query_collections_metadata,
                key=lambda m: m['name'],
            )
        except KeyError:
            metadata['query_collections'] = [
                {
                    "name": "allowed-queries",
                    "definition": {"queries": query_collections_metadata},
                }
            ]

        if self._hasura_config.rest:
            query_names = [q['name'] for q in query_collections_metadata]
            rest_endpoints_metadata = await self._generate_rest_endpoints_metadata(query_names)
            metadata['rest_endpoints'] = self._merge_metadata(
                existing=metadata.get('rest_endpoints', []),
                generated=rest_endpoints_metadata,
                key=lambda m: m['name'],
            )

        await self._replace_metadata(metadata)

        self._logger.info('Hasura instance has been configured')

    def _default_http_config(self) -> HTTPConfig:
        return HTTPConfig(
            cache=False,
            retry_sleep=1,
            retry_multiplier=1.1,
            ratelimit_rate=100,
            ratelimit_period=1,
        )

    async def _hasura_request(self, endpoint: str, json: Dict[str, Any]) -> Dict[str, Any]:
        self._logger.debug('Sending `%s` request: %s', endpoint, json)
        result = await self._http.request(
            method='post',
            cache=False,
            url=f'{self._hasura_config.url}/v1/{endpoint}',
            json=json,
            headers=self._hasura_config.headers,
        )
        self._logger.debug('Response: %s', result)
        if 'error' in result or 'errors' in result:
            raise HasuraError('Can\'t configure Hasura instance', result)
        return result

    async def _healthcheck(self) -> None:
        self._logger.info('Waiting for Hasura instance to be ready')
        for _ in range(self._hasura_config.connection_timeout):
            with suppress(ClientConnectorError, ClientOSError):
                response = await self._http._session.get(f'{self._hasura_config.url}/healthz')
                if response.status == 200:
                    break
            await asyncio.sleep(1)
        else:
            raise HasuraError(f'Hasura instance not responding for {self._hasura_config.connection_timeout} seconds')

    async def _reset_metadata(self) -> None:
        self._logger.info('Resetting metadata')
        await self._hasura_request(
            endpoint='metadata',
            json={
                "type": "clear_metadata",
                "args": {},
            },
        )

    async def _fetch_metadata(self) -> Dict[str, Any]:
        self._logger.info('Fetching existing metadata')
        return await self._hasura_request(
            endpoint='metadata',
            json={
                "type": "export_metadata",
                "args": {},
            },
        )

    async def _replace_metadata(self, metadata: Dict[str, Any]) -> None:
        self._logger.info('Replacing metadata')
        await self._hasura_request(
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

        for app, model in iter_models(self._package):
            table_name = model._meta.db_table or pascal_to_snake(model.__name__)
            model_tables[f'{app}.{model.__name__}'] = table_name
            metadata_tables[table_name] = self._format_table(table_name)

        for view in views:
            metadata_tables[view] = self._format_table(view)

        for app, model in iter_models(self._package):
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

    def _iterate_graphql_queries(self) -> Iterator[Tuple[str, str]]:
        package = importlib.import_module(self._package)
        package_path = dirname(package.__file__)
        graphql_path = join(package_path, 'graphql')
        for file in iter_files(graphql_path, '.graphql'):
            yield file.name.split('/')[-1][:-8], file.read()

    async def _generate_query_collections_metadata(self) -> List[Dict[str, Any]]:
        queries = []
        for _, model in iter_models(self._package):
            table_name = model._meta.db_table or pascal_to_snake(model.__name__)

            for field_name, field in model._meta.fields_map.items():
                if field.pk:
                    filter = field_name
                    break
            else:
                raise RuntimeError(f'Table `{table_name}` has no primary key. How is that possible?')

            table_name = f'{self._database_config.schema_name}_{table_name}'
            fields = await self._get_fields(table_name)
            queries.append(self._format_rest_query(table_name, table_name, filter, fields))

        for query_name, query in self._iterate_graphql_queries():
            queries.append(dict(name=query_name, query=query))

        return queries

    async def _generate_rest_endpoints_metadata(self, query_names: List[str]) -> List[Dict[str, Any]]:
        rest_endpoints = []
        for query_name in query_names:
            rest_endpoints.append(self._format_rest_endpoint(query_name))
        return rest_endpoints

    def _merge_metadata(self, existing: List[Dict[str, Any]], generated: List[Dict[str, Any]], key) -> List[Dict[str, Any]]:
        existing_dict = {key(t): t for t in existing}
        generated_dict = {key(t): t for t in generated}
        return list({**existing_dict, **generated_dict}.values())

    async def _get_fields_json(self, name: str) -> List[Dict[str, Any]]:
        result = await self._hasura_request(
            endpoint='graphql',
            json={
                'query': _get_fields_query,
                'variables': {'name': name},
            },
        )
        try:
            return result['data']['__type']['fields']
        except TypeError as e:
            raise HasuraError(f'Unknown table `{name}`') from e

    async def _get_fields(self, name: str = 'query_root') -> List[Field]:

        try:
            fields_json = await self._get_fields_json(name)
        except HasuraError:
            # NOTE: An issue with decamelizing the table name?
            # NOTE: dex_quotes_15m -> dexQuotes15m -> dex_quotes15m -> FAIL
            # NOTE: Let's prefix every numeric with underscore. Won't help in complex cases but worth a try.
            alternative_name = ''.join([f"_{w}" if w.isnumeric() else w for w in re.split(r'(\d+)', name)])
            fields_json = await self._get_fields_json(alternative_name)

        fields = []
        for field_json in fields_json:
            # NOTE: Exclude autogenerated aggregate and pk fields
            ignore_postfixes = ('_aggregate', '_by_pk', 'Aggregate', 'ByPk')
            if any(map(lambda postfix: field_json['name'].endswith(postfix), ignore_postfixes)):
                continue

            # NOTE: Exclude relations. Not reliable enough but ok for now.
            if (field_json['description'] or '').endswith('relationship'):
                continue

            # TODO: More precise matching
            try:
                type_ = field_json['type']['ofType']['name']
            except TypeError:
                type_ = field_json['type']['name']
            fields.append(
                Field(
                    name=field_json['name'],
                    type=type_,
                )
            )

        return fields

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
            columns = await self._get_fields(decamelized_table)
            custom_column_names = self._format_custom_column_names(columns)
            args: Dict[str, Any] = {
                'table': {
                    # NOTE: Remove schema prefix from table name
                    'name': decamelized_table.replace(self._database_config.schema_name, '')[1:],
                    'schema': self._database_config.schema_name,
                },
                'source': self._hasura_config.source,
                'configuration': {
                    'identifier': custom_root_fields['select_by_pk'],
                    'custom_root_fields': custom_root_fields,
                    'custom_column_names': custom_column_names,
                },
            }

            await self._hasura_request(
                endpoint='metadata',
                json={
                    'type': 'pg_set_table_customization',
                    'args': args,
                },
            )

    def _format_rest_query(self, name: str, table: str, filter: str, fields: List[Field]) -> Dict[str, Any]:
        if not table.endswith('_by_pk'):
            table += '_by_pk'
        name = humps.camelize(name) if self._hasura_config.camel_case else name
        filter = humps.camelize(filter) if self._hasura_config.camel_case else filter
        table = humps.camelize(table) if self._hasura_config.camel_case else table
        fields = [f.camelize() for f in fields] if self._hasura_config.camel_case else fields

        try:
            filter_field = next(f for f in fields if f.name == filter)
        except StopIteration as e:
            raise ConfigurationError(f'Table `{table}` has no column `{filter}`') from e

        query_arg = f'${filter_field.name}: {filter_field.type}!'
        query_filter = filter_field.name + ': $' + filter_field.name
        query_fields = ' '.join(f.name for f in fields)
        return {
            'name': name,
            'query': 'query ' + name + ' (' + query_arg + ') {' + table + '(' + query_filter + ') {' + query_fields + '}}',
        }

    def _format_rest_endpoint(self, query_name: str) -> Dict[str, Any]:
        return {
            "definition": {
                "query": {
                    "collection_name": "allowed-queries",
                    "query_name": query_name,
                },
            },
            "url": query_name,
            "methods": ["GET", "POST"],
            "name": query_name,
            "comment": None,
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
        return {humps.decamelize(f.name): humps.camelize(f.name) for f in fields}

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
