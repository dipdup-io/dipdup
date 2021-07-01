import asyncio
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

        self._logger.info('Hasura instance has been configured')

    async def close_session(self) -> None:
        await self._session.close()

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
        metadata = await http_request(
            self._session,
            'post',
            url=f'{self._hasura_config.url}/v1/query',
            json={
                "type": "export_metadata",
                "args": {},
            },
            headers=self._hasura_config.headers,
        )
        # TODO: Support multiple sources
        return metadata['sources'][0]

    async def _replace_metadata(self, metadata: Dict[str, Any]) -> None:
        self._logger.info('Replacing metadata')
        result = await http_request(
            self._session,
            'post',
            url=f'{self._hasura_config.url}/v1/query',
            json={
                "type": "replace_metadata",
                "args": metadata,
            },
            headers=self._hasura_config.headers,
        )
        if result.get('message') != 'success':
            raise HasuraError('Can\'t configure Hasura instance', result)

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
        """Generate metadata based on dapp models.

        Includes tables and their relations (but not entities created during execution of snippets from `sql` package directory)
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

    async def _get_fields(self, name: str = 'query_root') -> List[str]:
        query = (
            '''
            query introspectionQueryRoot {
                __type(name: "'''
            + name
            + '''") {
                    kind
                    name
                    fields {
                        name
                        description
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

        fields = result['data']['__type']['fields']
        return [
            f['name']
            for f in fields
            if not f['name'].endswith('_aggregate')
            and not f['name'].endswith('_by_pk')
            and not (f['description'] or '').endswith('relationship')
        ]

    async def _apply_camelcase(self) -> None:
        """Convert table and column names to camelCase.

        Slightly modified code from https://github.com/m-rgba/hasura-snake-to-camel
        """

        tables = await self._get_fields()

        # Inflect word to plural / singular
        p = inflect.engine()

        for table in tables:
            # De-camel any pre-camelized names
            table_decamel = humps.decamelize(table)

            # Split up words to lists
            words = table_decamel.split('_')

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
            jsondata: Dict[str, Any] = {}
            args: Dict[str, Any] = {}
            configuration = {}
            custom_root_fields = {}

            # Create Custom Root Field Payload
            jsondata['type'] = 'pg_set_table_customization'

            args['table'] = {
                'name': table.replace(self._database_config.schema_name, '')[1:],
                'schema': self._database_config.schema_name,
            }
            args['source'] = self._hasura_config.source
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

            columns = await self._get_fields(table)
            custom_column_names = {c: humps.camelize(c) for c in columns}

            jsondata['args'] = args
            args['configuration'] = configuration
            configuration['custom_root_fields'] = custom_root_fields
            configuration['custom_column_names'] = custom_column_names

            result = await http_request(
                self._session,
                'post',
                url=f'{self._hasura_config.url}/v1/metadata',
                json=jsondata,
                headers=self._hasura_config.headers,
            )
            if result.get('message') != 'success':
                raise HasuraError('Can\'t configure Hasura instance', result)

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
            "name": related_name,
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
            "name": name,
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
