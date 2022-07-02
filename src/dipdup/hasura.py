import asyncio
import hashlib
import importlib
import logging
import re
from contextlib import suppress
from http import HTTPStatus
from json import dumps as dump_json
from os.path import dirname
from os.path import join
from typing import Any
from typing import Dict
from typing import Iterable
from typing import Iterator
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union
from typing import cast

import humps
import orjson as json
from aiohttp import ClientConnectorError
from aiohttp import ClientOSError
from aiohttp import ClientResponseError
from aiohttp import ServerDisconnectedError
from pydantic.dataclasses import dataclass
from tortoise import fields

from dipdup.config import DEFAULT_POSTGRES_SCHEMA
from dipdup.config import HasuraConfig
from dipdup.config import HTTPConfig
from dipdup.config import PostgresDatabaseConfig
from dipdup.exceptions import ConfigurationError
from dipdup.exceptions import HasuraError
from dipdup.http import HTTPGateway
from dipdup.models import Schema
from dipdup.utils import iter_files
from dipdup.utils import pascal_to_snake
from dipdup.utils import snake_to_pascal
from dipdup.utils.database import get_connection
from dipdup.utils.database import iter_models

RelationalFieldT = Union[
    fields.relational.ForeignKeyFieldInstance,
    fields.relational.ManyToManyFieldInstance,
]
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
    type: Optional[str] = None

    def camelize(self) -> 'Field':
        return Field(
            name=humps.camelize(self.name),
            type=self.type,
        )

    @property
    def root(self) -> str:
        return humps.decamelize(self.name)


class HasuraGateway(HTTPGateway):
    _default_http_config = HTTPConfig(
        # NOTE: Does not apply to initial healthcheck
        retry_count=3,
        retry_sleep=1,
    )

    def __init__(
        self,
        package: str,
        hasura_config: HasuraConfig,
        database_config: PostgresDatabaseConfig,
        http_config: Optional[HTTPConfig] = None,
    ) -> None:
        super().__init__(hasura_config.url, self._default_http_config.merge(http_config))
        self._logger = logging.getLogger('dipdup.hasura')
        self._package = package
        self._hasura_config = hasura_config
        self._database_config = database_config

    async def configure(self, force: bool = False) -> None:
        """Generate Hasura metadata and apply to instance with credentials from `hasura` config section."""
        # TODO: Validate during config parsing
        if self._database_config.schema_name != DEFAULT_POSTGRES_SCHEMA:
            raise ConfigurationError('Hasura integration requires `schema_name` to be `public`')

        self._logger.info('Configuring Hasura')
        await self._healthcheck()

        hasura_schema_name = f'hasura_{self._hasura_config.url}'
        hasura_schema, _ = await Schema.get_or_create(name=hasura_schema_name, defaults={'hash': ''})
        metadata = await self._fetch_metadata()
        metadata_hash = self._hash_metadata(metadata)

        if not force and hasura_schema.hash == metadata_hash:
            self._logger.info('Metadata is up to date, no action required')
            return

        # NOTE: Find chosen source and overwrite its tables, create if missing and allowed.
        source_name = self._hasura_config.source

        if (source := self._get_source(metadata, source_name)) is None:
            if not self._hasura_config.create_source:
                raise HasuraError(f'Source `{source_name}` not found in metadata. Set `create_source` flag to create it.')

            await self._create_source()
            metadata = await self._fetch_metadata()
            if (source := self._get_source(metadata, source_name)) is None:
                raise HasuraError(f'Source `{source_name}` not found in metadata after creation.')

        source['tables'] = await self._generate_source_tables_metadata()

        # NOTE: Don't forget to invalidate old queries, customization will fail otherwise.
        metadata['query_collections'] = []
        metadata['rest_endpoints'] = []

        await self._replace_metadata(metadata)

        # NOTE: Apply table customizations before generating queries
        await self._apply_table_customization(source)
        metadata = await self._fetch_metadata()
        if (source := self._get_source(metadata, source_name)) is None:
            raise HasuraError(f'Source `{source_name}` not found in metadata after table customization.')

        # NOTE: Generate and apply queries and REST endpoints
        query_collections_metadata = await self._generate_query_collections_metadata()
        self._logger.info('Adding %s generated and user-defined queries', len(query_collections_metadata))
        metadata['query_collections'] = [
            {
                "name": "allowed-queries",
                "definition": {"queries": query_collections_metadata},
            }
        ]

        if self._hasura_config.rest:
            self._logger.info('Adding %s REST endpoints', len(query_collections_metadata))
            query_names = [q['name'] for q in query_collections_metadata]
            rest_endpoints_metadata = await self._generate_rest_endpoints_metadata(query_names)
            metadata['rest_endpoints'] = rest_endpoints_metadata

        await self._replace_metadata(metadata)

        # TODO: Find out why it is necessary
        # NOTE: Fetch metadata once again and save its hash for future comparisons
        metadata = await self._fetch_metadata()
        metadata_hash = self._hash_metadata(metadata)
        hasura_schema.hash = metadata_hash
        await hasura_schema.save()

        self._logger.info('Hasura instance has been configured')

    def _get_source(self, metadata: Dict[str, Any], name: str) -> Optional[Dict[str, Any]]:
        for source in metadata['sources']:
            if source['name'] == name:
                return source
        else:
            return None

    async def _hasura_request(self, endpoint: str, json: Dict[str, Any]) -> Dict[str, Any]:
        self._logger.debug('Sending `%s` request: %s', endpoint, dump_json(json))
        try:
            result = await self.request(
                method='post',
                url=f'{self._hasura_config.url}/v1/{endpoint}',
                json=json,
                headers=self._hasura_config.headers,
            )
        except ClientResponseError as e:
            raise HasuraError(f'{e.status} {e.message}') from e

        self._logger.debug('Response: %s', result)
        if errors := result.get('error') or result.get('errors'):
            raise HasuraError(errors)

        return result

    async def _healthcheck(self) -> None:
        self._logger.info('Waiting for Hasura instance to be ready')
        timeout = self._http_config.connection_timeout or 60
        for _ in range(timeout):
            with suppress(ClientConnectorError, ClientOSError, ServerDisconnectedError):
                response = await self._http._session.get(f'{self._hasura_config.url}/healthz')
                if response.status == HTTPStatus.OK:
                    break
            await asyncio.sleep(1)
        else:
            raise HasuraError(f'Not responding for {timeout} seconds')

        version_json = await (
            await self._http._session.get(
                f'{self._hasura_config.url}/v1/version',
            )
        ).json()
        version = version_json['version']
        if version.startswith('v1'):
            raise HasuraError('v1 is not supported, upgrade to the latest stable version.')

        self._logger.info('Connected to Hasura %s', version)

    async def _create_source(self) -> Dict[str, Any]:
        self._logger.info(f'Adding source `{self._hasura_config.source}`')
        return await self._hasura_request(
            endpoint='metadata',
            json={
                'type': 'pg_add_source',
                'args': {
                    'name': self._hasura_config.source,
                    'configuration': {
                        'connection_info': {
                            'database_url': {
                                'connection_parameters': self._database_config.hasura_connection_parameters,
                            },
                            'use_prepared_statements': True,
                        }
                    },
                    'replace_configuration': True,
                },
            },
        )

    async def _fetch_metadata(self) -> Dict[str, Any]:
        self._logger.info('Fetching existing metadata')
        return await self._hasura_request(
            endpoint='metadata',
            json={
                'type': 'export_metadata',
                'args': {},
            },
        )

    def _hash_metadata(self, metadata: Dict[str, Any]) -> str:
        return hashlib.sha256(json.dumps(metadata)).hexdigest()

    async def _replace_metadata(self, metadata: Dict[str, Any]) -> None:
        self._logger.info('Replacing metadata')
        endpoint, json = 'query', {
            'type': 'replace_metadata',
            'args': {
                'metadata': metadata,
            },
        }
        await self._hasura_request(endpoint, json)

    async def _get_views(self) -> List[str]:
        conn = get_connection()
        views = [
            row[0]
            for row in (
                await conn.execute_query(
                    f"SELECT table_name FROM information_schema.views WHERE table_schema = '{self._database_config.schema_name}' UNION "
                    f"SELECT matviewname as table_name FROM pg_matviews WHERE schemaname = '{self._database_config.schema_name}'"
                )
            )[1]
        ]
        self._logger.info('Found %s regular and materialized views', len(views))
        return views

    def _iterate_graphql_queries(self) -> Iterator[Tuple[str, str]]:
        package = importlib.import_module(self._package)
        package_path = dirname(cast(str, package.__file__))
        graphql_path = join(package_path, 'graphql')
        for file in iter_files(graphql_path, '.graphql'):
            yield file.name.split('/')[-1][:-8], file.read()

    async def _generate_source_tables_metadata(self) -> List[Dict[str, Any]]:
        """Generate source tables metadata based on project models and views.

        Includes tables and their relations.
        """

        self._logger.info('Generating Hasura metadata based on project models')
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
                    related_table_name = model_tables[field.model_name]
                    field_name = field.model_field_name
                    metadata_tables[table_name]['object_relationships'].append(
                        self._format_object_relationship(
                            name=field_name,
                            column=self._get_relation_source_field(field),
                        )
                    )
                    if field.related_name:
                        metadata_tables[related_table_name]['array_relationships'].append(
                            self._format_array_relationship(
                                related_name=field.related_name,
                                table=table_name,
                                column=self._get_relation_source_field(field),
                            )
                        )

                elif isinstance(field, fields.relational.ManyToManyFieldInstance):
                    related_table_name = model_tables[field.model_name]
                    junction_table_name = field.through

                    metadata_tables[junction_table_name] = self._format_table(junction_table_name)
                    metadata_tables[junction_table_name]['object_relationships'].append(
                        self._format_object_relationship(
                            name=related_table_name,
                            column=self._get_relation_source_field(field),
                        )
                    )
                    metadata_tables[junction_table_name]['object_relationships'].append(
                        self._format_object_relationship(
                            name=table_name,
                            column=self._get_relation_source_field(field),
                        )
                    )
                    if field.related_name:
                        metadata_tables[related_table_name]['array_relationships'].append(
                            self._format_array_relationship(
                                related_name=f'{related_table_name}_{field.related_name}',
                                table=junction_table_name,
                                column=self._get_relation_source_field(field),
                            )
                        )

                else:
                    pass

        return list(metadata_tables.values())

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

            fields = await self._get_fields(table_name)
            queries.append(
                self._format_rest_query(
                    name=table_name,
                    table=table_name,
                    filter=filter,
                    fields=fields,
                )
            )

        for query_name, query in self._iterate_graphql_queries():
            queries.append({'name': query_name, 'query': query})

        # NOTE: This is the only view we add by ourselves and thus know all params. Won't work for any view.
        queries.append(self._format_rest_head_status_query())

        return queries

    async def _generate_rest_endpoints_metadata(self, query_names: List[str]) -> List[Dict[str, Any]]:
        rest_endpoints = []
        for query_name in query_names:
            rest_endpoints.append(self._format_rest_endpoint(query_name))
        return rest_endpoints

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
        name = humps.decamelize(name)

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
            if any(field_json['name'].endswith(p) for p in ignore_postfixes):
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

    async def _apply_table_customization(self, source: Dict[str, Any]) -> None:
        """Convert table and column names to camelCase.

        Based on https://github.com/m-rgba/hasura-snake-to-camel
        """

        # NOTE: Build a set of table names for our source
        table_names = {t['table']['name'] for t in source['tables']}
        tables = await self._get_fields()

        # TODO: Bulk request
        for table in tables:
            if table.root not in table_names:
                continue

            custom_root_fields = self._format_custom_root_fields(table.root)
            columns = await self._get_fields(table.root)
            custom_column_names = self._format_custom_column_names(columns)
            args: Dict[str, Any] = {
                'table': self._format_table_table(table.root),
                'source': self._hasura_config.source,
                'configuration': {
                    'identifier': custom_root_fields['select_by_pk'],
                    'custom_root_fields': custom_root_fields,
                    'custom_column_names': custom_column_names,
                },
            }

            self._logger.info('Applying `%s` table customization', table.root)
            await self._hasura_request(
                endpoint='metadata',
                json={
                    'type': 'pg_set_table_customization',
                    'args': args,
                },
            )

    def _format_rest_query(self, name: str, table: str, filter: str, fields: Iterable[Field]) -> Dict[str, Any]:
        if not table.endswith('_by_pk'):
            table += '_by_pk'

        if self._hasura_config.camel_case:
            name = humps.camelize(name)
            filter = humps.camelize(filter)
            table = humps.camelize(table)
            fields = [f.camelize() for f in fields]

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

    def _format_rest_head_status_query(self) -> Dict[str, Any]:
        name = 'dipdup_head_status'
        if self._hasura_config.camel_case:
            name = humps.camelize(name)

        return {
            'name': name,
            'query': 'query ' + name + ' ($name: String!) {' + name + '(where: {name: {_eq: $name}}) {status}}',
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

    def _format_custom_root_fields(self, table_name: str) -> Dict[str, Any]:
        def _fmt(fmt: str) -> str:
            if self._hasura_config.camel_case:
                return humps.camelize(fmt.format(table_name))
            return humps.decamelize(fmt.format(table_name))

        # NOTE: Do not change original Hasura format, REST endpoints generation will be broken otherwise
        return {
            'select': _fmt('{}'),
            'select_by_pk': _fmt('{}_by_pk'),
            'select_aggregate': _fmt('{}_aggregate'),
            'insert': _fmt('insert_{}'),
            'insert_one': _fmt('insert_{}_one'),
            'update': _fmt('update_{}'),
            'update_by_pk': _fmt('update_{}_by_pk'),
            'delete': _fmt('delete_{}'),
            'delete_by_pk': _fmt('delete_{}_by_pk'),
        }

    def _format_custom_column_names(self, fields: List[Field]) -> Dict[str, Any]:
        if self._hasura_config.camel_case:
            return {humps.decamelize(f.name): humps.camelize(f.name) for f in fields}
        else:
            return {humps.decamelize(f.name): humps.decamelize(f.name) for f in fields}

    def _format_table(self, name: str) -> Dict[str, Any]:
        return {
            "table": self._format_table_table(name),
            "object_relationships": [],
            "array_relationships": [],
            "select_permissions": [
                self._format_select_permissions(),
            ],
        }

    def _format_table_table(self, name: str) -> Dict[str, Any]:
        return {
            "schema": self._database_config.schema_name,
            'name': name,
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

    def _get_relation_source_field(self, field: RelationalFieldT) -> str:
        if source_field := field.source_field:
            return field.model._meta.fields_db_projection[source_field]
        return field.model_field_name + '_id'
