import json
import logging
import os
import subprocess
from contextlib import suppress
from os import mkdir
from os.path import basename, dirname, exists, join, splitext
from shutil import rmtree
from typing import Any, Dict

from jinja2 import Template

from dipdup.config import BigMapIndexConfig, ContractConfig, ROLLBACK_HANDLER, DipDupConfig, OperationIndexConfig, TzktDatasourceConfig
from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.utils import camel_to_snake, snake_to_camel

_logger = logging.getLogger(__name__)


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
            self._datasources[datasource_config] = TzktDatasource(datasource_config.url)
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


async def fetch_schemas(config: DipDupConfig):
    _logger.info('Creating `schemas` package')
    schemas_path = join(config.package_path, 'schemas')
    with suppress(FileExistsError):
        mkdir(schemas_path)

    schemas_cache = SchemasCache()

    for index_name, index_config in config.indexes.items():
        if isinstance(index_config, OperationIndexConfig):
            for handler_config in index_config.handlers:
                for pattern_config in handler_config.pattern:
                    contract_config = pattern_config.contract_config
                    contract_schemas = await schemas_cache.get(index_config.datasource_config, contract_config)

                    contract_schemas_path = join(schemas_path, contract_config.module_name)
                    with suppress(FileExistsError):
                        mkdir(contract_schemas_path)

                    storage_schema_path = join(contract_schemas_path, 'storage.json')

                    storage_schema = contract_schemas['storageSchema']
                    if not exists(storage_schema_path):
                        with open(storage_schema_path, 'w') as file:
                            file.write(json.dumps(storage_schema, indent=4, sort_keys=True))

                    parameter_schemas_path = join(contract_schemas_path, 'parameter')
                    with suppress(FileExistsError):
                        mkdir(parameter_schemas_path)

                    entrypoint_schema = next(
                        ep['parameterSchema'] for ep in contract_schemas['entrypoints'] if ep['name'] == pattern_config.entrypoint
                    )
                    entrypoint_schema_path = join(parameter_schemas_path, f'{pattern_config.entrypoint}.json')

                    if not exists(entrypoint_schema_path):
                        with open(entrypoint_schema_path, 'w') as file:
                            file.write(json.dumps(entrypoint_schema, indent=4))
                    elif contract_config.typename is not None:
                        with open(entrypoint_schema_path, 'r') as file:
                            existing_schema = json.loads(file.read())
                        if entrypoint_schema != existing_schema:
                            # FIXME: Different field order counts as different schema
                            # raise ValueError(f'Contract "{contract.address}" falsely claims to be a "{contract.typename}"')
                            _logger.warning('Contract "%s" falsely claims to be a "%s"', contract_config.address, contract_config.typename)

        elif isinstance(index_config, BigMapIndexConfig):
            datasource = TzktDatasource(index_config.datasource_config.url)
            for handler_config in index_config.handlers:
                for pattern_config in handler_config.pattern:
                    contract_config = pattern_config.contract_config

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
                # handler_code = operation_handler_template.render(
                #     package=config.package,
                #     handler=handler.callback,
                #     patterns=handler.pattern,
                #     snake_to_camel=snake_to_camel,
                #     camel_to_snake=camel_to_snake,
                # )
                # handler_path = join(handlers_path, f'{handler.callback}.py')
                # if not exists(handler_path):
                #     with open(handler_path, 'w') as file:
                #         file.write(handler_code)
        
        else:
            raise NotImplementedError(f'Index kind `{index_config.kind}` is not supported')




async def cleanup(config: DipDupConfig):
    _logger.info('Cleaning up')
    schemas_path = join(config.package_path, 'schemas')
    rmtree(schemas_path)
