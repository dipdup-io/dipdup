import json
import logging
import os
import subprocess
from contextlib import suppress
from os import mkdir
from os.path import basename, dirname, exists, join, splitext
from shutil import rmtree
from typing import Any, Dict, cast

from jinja2 import Template

from dipdup.config import (
    ROLLBACK_HANDLER,
    BigMapIndexConfig,
    ContractConfig,
    DipDupConfig,
    DynamicTemplateConfig,
    OperationHandlerConfig,
    OperationHandlerOriginationPatternConfig,
    OperationHandlerTransactionPatternConfig,
    OperationIndexConfig,
    StaticTemplateConfig,
    TzktDatasourceConfig,
)
from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.exceptions import ConfigurationError
from dipdup.utils import camel_to_snake, snake_to_camel

_logger = logging.getLogger(__name__)


def resolve_big_maps(schema: Dict[str, Any]) -> Dict[str, Any]:
    if 'properties' in schema:
        return {
            **schema,
            'properties': {prop: resolve_big_maps(sub_schema) for prop, sub_schema in schema['properties'].items()},
        }
    elif schema.get('$comment') == 'big_map':
        return schema['oneOf'][1]
    else:
        return schema


class SchemasCache:
    def __init__(self) -> None:
        self._logger = logging.getLogger(f'{__name__}.{self.__class__.__qualname__}')
        self._datasources: Dict[TzktDatasourceConfig, TzktDatasource] = {}
        self._schemas: Dict[TzktDatasourceConfig, Dict[str, Dict[str, Any]]] = {}

    async def get(
        self,
        datasource_config: TzktDatasourceConfig,
        contract_config: ContractConfig,
    ) -> Dict[str, Any]:
        if datasource_config not in self._datasources:
            self._datasources[datasource_config] = TzktDatasource(datasource_config.url, True)
            self._schemas[datasource_config] = {}
        if contract_config.address not in self._schemas[datasource_config]:
            self._logger.info('Fetching schemas for contract `%s`', contract_config.address)
            address_schemas_json = await self._datasources[datasource_config].fetch_jsonschemas(contract_config.address)
            self._schemas[datasource_config][contract_config.address] = address_schemas_json
        return self._schemas[datasource_config][contract_config.address]


async def create_package(config: DipDupConfig):
    try:
        package_path = config.package_path
    except (ImportError, ModuleNotFoundError):
        package_path = join(os.getcwd(), config.package)
        mkdir(package_path)
        with open(join(package_path, '__init__.py'), 'w'):
            pass

    models_path = join(package_path, 'models.py')
    if not exists(models_path):
        with open(join(dirname(__file__), 'templates', 'models.py.j2')) as file:
            template = Template(file.read())
        models_code = template.render()
        with open(models_path, 'w') as file:
            file.write(models_code)


async def resolve_dynamic_templates(config: DipDupConfig) -> None:
    for index_name, index_config in config.indexes.items():
        if isinstance(index_config, DynamicTemplateConfig):
            config.indexes[index_name] = StaticTemplateConfig(
                template=index_config.template,
                values=dict(contract=cast(str, index_config.similar_to)),
            )
            config.pre_initialize()
            index_config = config.indexes[index_name]


async def fetch_schemas(config: DipDupConfig) -> None:
    _logger.info('Creating `schemas` package')
    schemas_path = join(config.package_path, 'schemas')
    with suppress(FileExistsError):
        mkdir(schemas_path)

    schemas_cache = SchemasCache()

    for index_config in config.indexes.values():

        if isinstance(index_config, OperationIndexConfig):
            for operation_handler_config in index_config.handlers:
                for operation_pattern_config in operation_handler_config.pattern:

                    if (
                        isinstance(operation_pattern_config, OperationHandlerTransactionPatternConfig)
                        and operation_pattern_config.entrypoint
                    ):
                        contract_config = operation_pattern_config.destination_contract_config
                    elif isinstance(operation_pattern_config, OperationHandlerOriginationPatternConfig):
                        contract_config = operation_pattern_config.contract_config
                    else:
                        continue

                    contract_schemas = await schemas_cache.get(index_config.datasource_config, contract_config)

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
                            _logger.warning('Contract "%s" falsely claims to be a "%s"', contract_config.address, contract_config.typename)

        elif isinstance(index_config, BigMapIndexConfig):
            for big_map_handler_config in index_config.handlers:
                for big_map_pattern_config in big_map_handler_config.pattern:
                    contract_config = big_map_pattern_config.contract_config

                    contract_schemas = await schemas_cache.get(index_config.datasource_config, contract_config)

                    contract_schemas_path = join(schemas_path, contract_config.module_name)
                    with suppress(FileExistsError):
                        mkdir(contract_schemas_path)

                    big_map_schemas_path = join(contract_schemas_path, 'big_map')
                    with suppress(FileExistsError):
                        mkdir(big_map_schemas_path)

                    try:
                        big_map_schema = next(ep for ep in contract_schemas['bigMaps'] if ep['path'] == big_map_pattern_config.path)
                    except StopIteration as e:
                        raise ConfigurationError(
                            f'Contract `{contract_config.address}` has no big map path `{big_map_pattern_config.path}`'
                        ) from e
                    big_map_key_schema = big_map_schema['keySchema']
                    big_map_key_schema_path = join(big_map_schemas_path, f'{big_map_pattern_config.path}.key.json')

                    if not exists(big_map_key_schema_path):
                        with open(big_map_key_schema_path, 'w') as file:
                            file.write(json.dumps(big_map_key_schema, indent=4))

                    big_map_value_schema = big_map_schema['valueSchema']
                    big_map_value_schema_path = join(big_map_schemas_path, f'{big_map_pattern_config.path}.value.json')

                    if not exists(big_map_value_schema_path):
                        with open(big_map_value_schema_path, 'w') as file:
                            file.write(json.dumps(big_map_value_schema, indent=4))

        elif isinstance(index_config, StaticTemplateConfig):
            raise RuntimeError('Config is not initialized')

        else:
            raise NotImplementedError(f'Index kind `{index_config.kind}` is not supported')


async def generate_types(config: DipDupConfig):
    schemas_path = join(config.package_path, 'schemas')
    types_path = join(config.package_path, 'types')

    _logger.info('Creating `types` package')
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
            output_path = join(types_root, f'{camel_to_snake(name)}.py')

            if name == 'storage':
                name = '_'.join([root.split('/')[-1], name])
            if root.split('/')[-1] == 'parameter':
                name += '_parameter'

            _logger.info('Generating type `%s`', name)
            subprocess.run(
                [
                    'datamodel-codegen',
                    '--input',
                    input_path,
                    '--output',
                    output_path,
                    '--class-name',
                    snake_to_camel(name),
                    '--disable-timestamp',
                    '--use-default',
                ],
                check=True,
            )


async def generate_handlers(config: DipDupConfig):
    _logger.info('Loading handler templates')
    with open(join(dirname(__file__), 'templates', 'operation_handler.py.j2')) as file:
        operation_handler_template = Template(file.read())
    with open(join(dirname(__file__), 'templates', 'big_map_handler.py.j2')) as file:
        big_map_handler_template = Template(file.read())
    with open(join(dirname(__file__), 'templates', f'{ROLLBACK_HANDLER}.py.j2')) as file:
        rollback_template = Template(file.read())

    _logger.info('Creating `handlers` package')
    handlers_path = join(config.package_path, 'handlers')
    with suppress(FileExistsError):
        mkdir(handlers_path)
        with open(join(handlers_path, '__init__.py'), 'w'):
            pass

    _logger.info('Generating handler `%s`', ROLLBACK_HANDLER)
    handler_code = rollback_template.render()
    handler_path = join(handlers_path, f'{ROLLBACK_HANDLER}.py')
    if not exists(handler_path):
        with open(handler_path, 'w') as file:
            file.write(handler_code)

    for index_config in config.indexes.values():
        if isinstance(index_config, OperationIndexConfig):
            for handler_config in index_config.handlers:
                _logger.info('Generating handler `%s`', handler_config.callback)
                handler_code = operation_handler_template.render(
                    package=config.package,
                    handler=handler_config.callback,
                    patterns=handler_config.pattern,
                    snake_to_camel=snake_to_camel,
                    camel_to_snake=camel_to_snake,
                )
                handler_path = join(handlers_path, f'{handler_config.callback}.py')
                if not exists(handler_path):
                    with open(handler_path, 'w') as file:
                        file.write(handler_code)

        elif isinstance(index_config, BigMapIndexConfig):
            for handler in index_config.handlers:
                _logger.info('Generating handler `%s`', handler.callback)
                for pattern_config in handler.pattern:
                    pattern_config.path = pattern_config.path.replace('.', '_')
                handler_code = big_map_handler_template.render(
                    package=config.package,
                    handler=handler.callback,
                    patterns=handler.pattern,
                    snake_to_camel=snake_to_camel,
                    camel_to_snake=camel_to_snake,
                )
                handler_path = join(handlers_path, f'{handler.callback}.py')
                if not exists(handler_path):
                    with open(handler_path, 'w') as file:
                        file.write(handler_code)

        else:
            raise NotImplementedError(f'Index kind `{index_config.kind}` is not supported')


async def cleanup(config: DipDupConfig):
    _logger.info('Cleaning up')
    schemas_path = join(config.package_path, 'schemas')
    rmtree(schemas_path)
