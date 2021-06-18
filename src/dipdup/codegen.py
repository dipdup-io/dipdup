import json
import logging
import os
import subprocess
from contextlib import suppress
from copy import copy
from os import mkdir
from os.path import basename, dirname, exists, join, splitext
from shutil import rmtree
from typing import Any, Dict

from jinja2 import Template

from dipdup.config import (
    CONFIGURE_HANDLER,
    ROLLBACK_HANDLER,
    BigMapIndexConfig,
    ContractConfig,
    DatasourceConfigT,
    DipDupConfig,
    OperationHandlerOriginationPatternConfig,
    OperationHandlerTransactionPatternConfig,
    OperationIndexConfig,
    StaticTemplateConfig,
    TzktDatasourceConfig,
)
from dipdup.datasources import DatasourceT
from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.exceptions import ConfigurationError
from dipdup.utils import pascal_to_snake, snake_to_pascal


def resolve_big_maps(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Preprocess bigmaps in JSONSchema. Those are unions as could be pointers.
    We resolve bigmaps from diffs so no need to include int in type signature."""
    if 'properties' in schema:
        return {
            **schema,
            'properties': {prop: resolve_big_maps(sub_schema) for prop, sub_schema in schema['properties'].items()},
        }
    elif schema.get('$comment') == 'big_map':
        return schema['oneOf'][1]
    else:
        return schema


class DipDupCodeGenerator:
    """Generates package based on config, invoked from `init` CLI command"""

    def __init__(self, config: DipDupConfig, datasources: Dict[DatasourceConfigT, DatasourceT]) -> None:
        self._logger = logging.getLogger(__name__)
        self._config = config
        self._datasources = datasources
        self._schemas: Dict[TzktDatasourceConfig, Dict[str, Dict[str, Any]]] = {}

    async def create_package(self) -> None:
        """Create Python package skeleton if not exists"""
        self._logger.info('Creating package `%s`', self._config.package)
        try:
            package_path = self._config.package_path
        except (ImportError, ModuleNotFoundError):
            package_path = join(os.getcwd(), self._config.package)
            mkdir(package_path)
            with open(join(package_path, '__init__.py'), 'w'):
                pass

        self._logger.info('Creating `%s.models` module', self._config.package)
        models_path = join(package_path, 'models.py')
        if not exists(models_path):
            with open(join(dirname(__file__), 'templates', 'models.py.j2')) as file:
                template = Template(file.read())
            models_code = template.render()
            with open(models_path, 'w') as file:
                file.write(models_code)

        self._logger.info('Creating `%s.handlers` package', self._config.package)
        handlers_path = join(self._config.package_path, 'handlers')
        with suppress(FileExistsError):
            mkdir(handlers_path)
            with open(join(handlers_path, '__init__.py'), 'w'):
                pass

    async def fetch_schemas(self) -> None:
        """Fetch JSONSchemas for all contracts used in config"""
        self._logger.info('Creating `schemas` package')
        schemas_path = join(self._config.package_path, 'schemas')
        with suppress(FileExistsError):
            mkdir(schemas_path)

        for index_config in self._config.indexes.values():

            if isinstance(index_config, OperationIndexConfig):
                for operation_handler_config in index_config.handlers:
                    for operation_pattern_config in operation_handler_config.pattern:

                        if (
                            isinstance(operation_pattern_config, OperationHandlerTransactionPatternConfig)
                            and operation_pattern_config.entrypoint
                        ):
                            contract_config = operation_pattern_config.destination_contract_config
                            originated = False
                        elif isinstance(operation_pattern_config, OperationHandlerOriginationPatternConfig):
                            contract_config = operation_pattern_config.contract_config
                            originated = bool(operation_pattern_config.source)
                        else:
                            continue

                        self._logger.debug(contract_config)
                        contract_schemas = await self._get_schema(index_config.datasource_config, contract_config, originated)

                        contract_schemas_path = join(schemas_path, contract_config.module_name)
                        with suppress(FileExistsError):
                            mkdir(contract_schemas_path)

                        storage_schema_path = join(contract_schemas_path, 'storage.json')

                        storage_schema = resolve_big_maps(contract_schemas['storageSchema'])
                        if not exists(storage_schema_path):
                            with open(storage_schema_path, 'w') as file:
                                file.write(json.dumps(storage_schema, indent=4, sort_keys=True))

                        if not isinstance(operation_pattern_config, OperationHandlerTransactionPatternConfig):
                            continue

                        parameter_schemas_path = join(contract_schemas_path, 'parameter')
                        with suppress(FileExistsError):
                            mkdir(parameter_schemas_path)

                        try:
                            entrypoint_schema = next(
                                ep['parameterSchema']
                                for ep in contract_schemas['entrypoints']
                                if ep['name'] == operation_pattern_config.entrypoint
                            )
                        except StopIteration as e:
                            raise ConfigurationError(
                                f'Contract `{contract_config.address}` has no entrypoint `{operation_pattern_config.entrypoint}`'
                            ) from e

                        entrypoint_schema_path = join(parameter_schemas_path, f'{operation_pattern_config.entrypoint}.json')

                        if not exists(entrypoint_schema_path):
                            with open(entrypoint_schema_path, 'w') as file:
                                file.write(json.dumps(entrypoint_schema, indent=4))
                        elif contract_config.typename is not None:
                            with open(entrypoint_schema_path, 'r') as file:
                                existing_schema = json.loads(file.read())
                            if entrypoint_schema != existing_schema:
                                self._logger.warning(
                                    'Contract "%s" falsely claims to be a "%s"', contract_config.address, contract_config.typename
                                )

            elif isinstance(index_config, BigMapIndexConfig):
                for big_map_handler_config in index_config.handlers:
                    contract_config = big_map_handler_config.contract_config

                    contract_schemas = await self._get_schema(index_config.datasource_config, contract_config, False)

                    contract_schemas_path = join(schemas_path, contract_config.module_name)
                    with suppress(FileExistsError):
                        mkdir(contract_schemas_path)

                    big_map_schemas_path = join(contract_schemas_path, 'big_map')
                    with suppress(FileExistsError):
                        mkdir(big_map_schemas_path)

                    try:
                        big_map_schema = next(ep for ep in contract_schemas['bigMaps'] if ep['path'] == big_map_handler_config.path)
                    except StopIteration as e:
                        raise ConfigurationError(
                            f'Contract `{contract_config.address}` has no big map path `{big_map_handler_config.path}`'
                        ) from e
                    big_map_key_schema = big_map_schema['keySchema']
                    big_map_key_schema_path = join(big_map_schemas_path, f'{big_map_handler_config.path}.key.json')

                    if not exists(big_map_key_schema_path):
                        with open(big_map_key_schema_path, 'w') as file:
                            file.write(json.dumps(big_map_key_schema, indent=4))

                    big_map_value_schema = big_map_schema['valueSchema']
                    big_map_value_schema_path = join(big_map_schemas_path, f'{big_map_handler_config.path}.value.json')

                    if not exists(big_map_value_schema_path):
                        with open(big_map_value_schema_path, 'w') as file:
                            file.write(json.dumps(big_map_value_schema, indent=4))

            elif isinstance(index_config, StaticTemplateConfig):
                raise RuntimeError('Config is not pre-initialized')

            else:
                raise NotImplementedError(f'Index kind `{index_config.kind}` is not supported')

    async def generate_types(self) -> None:
        """Generate typeclasses from fetched JSONSchemas: contract's storage, parameter, big map keys/values."""
        schemas_path = join(self._config.package_path, 'schemas')
        types_path = join(self._config.package_path, 'types')

        self._logger.info('Creating `types` package')
        with suppress(FileExistsError):
            mkdir(types_path)
            with open(join(types_path, '__init__.py'), 'w'):
                pass

        for root, dirs, files in os.walk(schemas_path):
            types_root = root.replace(schemas_path, types_path)

            for dir in dirs:
                dir_path = join(types_root, dir)
                with suppress(FileExistsError):
                    os.mkdir(dir_path)
                    with open(join(dir_path, '__init__.py'), 'w'):
                        pass

            for file in files:
                name, ext = splitext(basename(file))
                if ext != '.json':
                    continue

                input_path = join(root, file)
                output_path = join(types_root, f'{pascal_to_snake(name)}.py')

                if name == 'storage':
                    name = '_'.join([root.split('/')[-1], name])
                if root.split('/')[-1] == 'parameter':
                    name += '_parameter'

                self._logger.info('Generating type `%s`', name)
                args = [
                    'datamodel-codegen',
                    '--input',
                    input_path,
                    '--output',
                    output_path,
                    '--class-name',
                    snake_to_pascal(name),
                    '--disable-timestamp',
                    '--use-default',
                ]
                self._logger.debug(' '.join(args))
                subprocess.run(args, check=True)

    async def generate_default_handlers(self, recreate=False) -> None:
        handlers_path = join(self._config.package_path, 'handlers')
        with open(join(dirname(__file__), 'templates', f'{ROLLBACK_HANDLER}.py.j2')) as file:
            rollback_template = Template(file.read())
        with open(join(dirname(__file__), 'templates', f'{CONFIGURE_HANDLER}.py.j2')) as file:
            configure_template = Template(file.read())

        self._logger.info('Generating handler `%s`', CONFIGURE_HANDLER)
        handler_code = configure_template.render()
        handler_path = join(handlers_path, f'{CONFIGURE_HANDLER}.py')
        if not exists(handler_path) or recreate:
            with open(handler_path, 'w') as file:
                file.write(handler_code)

        self._logger.info('Generating handler `%s`', ROLLBACK_HANDLER)
        handler_code = rollback_template.render()
        handler_path = join(handlers_path, f'{ROLLBACK_HANDLER}.py')
        if not exists(handler_path) or recreate:
            with open(handler_path, 'w') as file:
                file.write(handler_code)

    async def generate_user_handlers(self) -> None:
        """Generate handler stubs with typehints from templates if not exist"""
        handlers_path = join(self._config.package_path, 'handlers')
        with open(join(dirname(__file__), 'templates', 'operation_handler.py.j2')) as file:
            operation_handler_template = Template(file.read())
        with open(join(dirname(__file__), 'templates', 'big_map_handler.py.j2')) as file:
            big_map_handler_template = Template(file.read())

        for index_config in self._config.indexes.values():
            if isinstance(index_config, OperationIndexConfig):
                for handler_config in index_config.handlers:
                    self._logger.info('Generating handler `%s`', handler_config.callback)
                    handler_code = operation_handler_template.render(
                        package=self._config.package,
                        handler=handler_config.callback,
                        patterns=handler_config.pattern,
                        snake_to_pascal=snake_to_pascal,
                        pascal_to_snake=pascal_to_snake,
                    )
                    handler_path = join(handlers_path, f'{handler_config.callback}.py')
                    if not exists(handler_path):
                        with open(handler_path, 'w') as file:
                            file.write(handler_code)

            elif isinstance(index_config, BigMapIndexConfig):
                for big_map_handler_config in index_config.handlers:
                    self._logger.info('Generating handler `%s`', big_map_handler_config.callback)
                    handler_path = big_map_handler_config.path.replace('.', '_')
                    handler_code = big_map_handler_template.render(
                        package=self._config.package,
                        handler=big_map_handler_config,
                        handler_path=handler_path,
                        snake_to_pascal=snake_to_pascal,
                        pascal_to_snake=pascal_to_snake,
                    )
                    handler_path = join(handlers_path, f'{big_map_handler_config.callback}.py')
                    if not exists(handler_path):
                        with open(handler_path, 'w') as file:
                            file.write(handler_code)

            else:
                raise NotImplementedError(f'Index kind `{index_config.kind}` is not supported')

    async def cleanup(self) -> None:
        """Remove fetched JSONSchemas"""
        self._logger.info('Cleaning up')
        schemas_path = join(self._config.package_path, 'schemas')
        rmtree(schemas_path)

    async def _get_schema(
        self,
        datasource_config: TzktDatasourceConfig,
        contract_config: ContractConfig,
        originated: bool,
    ) -> Dict[str, Any]:
        """Get contract JSONSchema from TzKT or from cache"""
        datasource = self._datasources.get(datasource_config)
        address = contract_config.address
        if datasource is None:
            raise RuntimeError('Call `create_datasources` first')
        if not isinstance(datasource, TzktDatasource):
            raise RuntimeError
        if datasource_config not in self._schemas:
            self._schemas[datasource_config] = {}
        if address not in self._schemas[datasource_config]:
            if originated:
                address = (await datasource.get_originated_contracts(address))[0]
                self._logger.info('Fetching schemas for contract `%s` (originated from `%s`)', address, contract_config.address)
            else:
                self._logger.info('Fetching schemas for contract `%s`', address)

            address_schemas_json = await datasource.get_jsonschemas(address)
            self._schemas[datasource_config][address] = address_schemas_json
        return self._schemas[datasource_config][address]

    async def migrate_user_handlers_to_v1(self) -> None:
        remove_lines = [
            'from dipdup.models import',
            'from dipdup.context import',
            'from dipdup.utils import reindex',
        ]
        add_lines = [
            'from dipdup.models import OperationData, Transaction, Origination, BigMapDiff, BigMapData, BigMapAction',
            'from dipdup.context import HandlerContext, RollbackHandlerContext',
        ]
        replace_table = {
            'TransactionContext': 'Transaction',
            'OriginationContext': 'Origination',
            'BigMapContext': 'BigMapDiff',
            'OperationHandlerContext': 'HandlerContext',
            'BigMapHandlerContext': 'HandlerContext',
        }
        handlers_path = join(self._config.package_path, 'handlers')

        for root, _, files in os.walk(handlers_path):
            for filename in files:
                if filename == '__init__.py' or not filename.endswith('.py'):
                    continue
                path = join(root, filename)
                newfile = copy(add_lines)
                with open(path) as file:
                    for line in file.read().split('\n'):
                        # Skip existing models imports
                        if any(map(lambda l: l in line, remove_lines)):
                            continue
                        # Replace by table
                        for from_, to in replace_table.items():
                            line = line.replace(from_, to)
                        newfile.append(line)
                with open(path, 'w') as file:
                    file.write('\n'.join(newfile))
