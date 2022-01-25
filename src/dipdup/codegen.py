import json
import logging
import os
import re
import subprocess
from copy import copy
from os.path import basename
from os.path import dirname
from os.path import exists
from os.path import join
from os.path import relpath
from os.path import splitext
from shutil import rmtree
from typing import Any
from typing import Dict
from typing import List
from typing import cast

from jinja2 import Template

from dipdup import __version__
from dipdup.config import BigMapIndexConfig
from dipdup.config import CallbackMixin
from dipdup.config import ContractConfig
from dipdup.config import DatasourceConfigT
from dipdup.config import DipDupConfig
from dipdup.config import HandlerConfig
from dipdup.config import HeadIndexConfig
from dipdup.config import IndexTemplateConfig
from dipdup.config import OperationHandlerOriginationPatternConfig
from dipdup.config import OperationHandlerTransactionPatternConfig
from dipdup.config import OperationIndexConfig
from dipdup.config import TzktDatasourceConfig
from dipdup.config import default_hooks
from dipdup.datasources.datasource import Datasource
from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.exceptions import ConfigInitializationException
from dipdup.exceptions import ConfigurationError
from dipdup.utils import import_submodules
from dipdup.utils import mkdir_p
from dipdup.utils import pascal_to_snake
from dipdup.utils import snake_to_pascal
from dipdup.utils import touch
from dipdup.utils import write

DEFAULT_DOCKER_ENV_FILE_CONTENT = {
    'POSTGRES_USER': 'dipdup',
    'POSTGRES_DB': 'dipdup',
    'POSTGRES_PASSWORD': 'changeme',
    'HASURA_GRAPHQL_DATABASE_URL': 'postgres://dipdup:changeme@db:5432/dipdup',
    'HASURA_GRAPHQL_ENABLE_CONSOLE': 'true',
    'HASURA_GRAPHQL_ADMIN_INTERNAL_ERRORS': 'true',
    'HASURA_GRAPHQL_ENABLED_LOG_TYPES': 'startup, http-log, webhook-log, websocket-log, query-log',
    'HASURA_GRAPHQL_ADMIN_SECRET': 'changeme',
    'HASURA_GRAPHQL_UNAUTHORIZED_ROLE': 'user',
}
DEFAULT_DOCKER_IMAGE = 'dipdup/dipdup'
DEFAULT_DOCKER_TAG = __version__
DEFAULT_DOCKER_ENV_FILE = 'dipdup.env'

_templates: Dict[str, Template] = {}


def preprocess_storage_jsonschema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Preprocess bigmaps in JSONSchema. Those are unions as could be pointers.
    We resolve bigmaps from diffs so no need to include int in type signature."""
    if not isinstance(schema, dict):
        return schema
    if 'oneOf' in schema:
        schema['oneOf'] = [preprocess_storage_jsonschema(sub_schema) for sub_schema in schema['oneOf']]
    if 'properties' in schema:
        return {
            **schema,
            'properties': {prop: preprocess_storage_jsonschema(sub_schema) for prop, sub_schema in schema['properties'].items()},
        }
    elif 'items' in schema:
        return {
            **schema,
            'items': preprocess_storage_jsonschema(schema['items']),
        }
    elif 'additionalProperties' in schema:
        return {
            **schema,
            'additionalProperties': preprocess_storage_jsonschema(schema['additionalProperties']),
        }
    elif schema.get('$comment') == 'big_map':
        return schema['oneOf'][1]
    else:
        return schema


def load_template(name: str) -> Template:
    """Load template from templates/{name}.j2"""
    if name not in _templates:
        with open(join(dirname(__file__), 'templates', name + '.j2'), 'r') as f:
            return Template(f.read())
    return _templates[name]


class DipDupCodeGenerator:
    """Generates package based on config, invoked from `init` CLI command"""

    def __init__(self, config: DipDupConfig, datasources: Dict[DatasourceConfigT, Datasource]) -> None:
        self._logger = logging.getLogger('dipdup.codegen')
        self._config = config
        self._datasources = datasources
        self._schemas: Dict[TzktDatasourceConfig, Dict[str, Dict[str, Any]]] = {}

    async def init(self, overwrite_types: bool = False, keep_schemas: bool = False) -> None:
        self._logger.info('Initializing project')
        await self.create_package()
        await self.fetch_schemas()
        await self.generate_types(overwrite_types)
        await self.generate_hooks()
        await self.generate_handlers()
        if not keep_schemas:
            await self.cleanup()
        await self.verify_package()

    async def docker_init(self, image: str, tag: str, env_file: str) -> None:
        self._logger.info('Initializing Docker inventory')
        await self.generate_docker(image, tag, env_file)
        await self.verify_package()

    async def create_package(self) -> None:
        """Create Python package skeleton if not exists"""
        try:
            package_path = self._config.package_path
        except ImportError:
            self._logger.info('Creating package `%s`', self._config.package)
            package_path = join(os.getcwd(), self._config.package)

        touch(join(package_path, '__init__.py'))

        models_path = join(package_path, 'models.py')
        if not exists(models_path):
            template = load_template('models.py')
            models_code = template.render()
            write(models_path, models_code)

        for subpackage in ('handlers', 'hooks'):
            subpackage_path = join(self._config.package_path, subpackage)
            touch(join(subpackage_path, '__init__.py'))

        sql_path = join(self._config.package_path, 'sql')
        touch(join(sql_path, '.keep'))

        graphql_path = join(self._config.package_path, 'graphql')
        touch(join(graphql_path, '.keep'))

    async def fetch_schemas(self) -> None:
        """Fetch JSONSchemas for all contracts used in config"""
        self._logger.info('Creating `schemas` directory')
        schemas_path = join(self._config.package_path, 'schemas')
        mkdir_p(schemas_path)

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
                            # NOTE: Operations without entrypoint are untyped
                            continue

                        self._logger.debug(contract_config)
                        contract_schemas = await self._get_schema(index_config.datasource_config, contract_config, originated)

                        contract_schemas_path = join(schemas_path, contract_config.module_name)
                        mkdir_p(contract_schemas_path)

                        storage_schema_path = join(contract_schemas_path, 'storage.json')
                        storage_schema = preprocess_storage_jsonschema(contract_schemas['storageSchema'])

                        write(storage_schema_path, json.dumps(storage_schema, indent=4, sort_keys=True))

                        if not isinstance(operation_pattern_config, OperationHandlerTransactionPatternConfig):
                            continue

                        parameter_schemas_path = join(contract_schemas_path, 'parameter')
                        entrypoint = cast(str, operation_pattern_config.entrypoint)
                        mkdir_p(parameter_schemas_path)

                        try:
                            entrypoint_schema = next(
                                ep['parameterSchema'] for ep in contract_schemas['entrypoints'] if ep['name'] == entrypoint
                            )
                        except StopIteration as e:
                            raise ConfigurationError(f'Contract `{contract_config.address}` has no entrypoint `{entrypoint}`') from e

                        entrypoint = entrypoint.replace('.', '_').lstrip('_')
                        entrypoint_schema_path = join(parameter_schemas_path, f'{entrypoint}.json')
                        written = write(entrypoint_schema_path, json.dumps(entrypoint_schema, indent=4))
                        if not written and contract_config.typename is not None:
                            with open(entrypoint_schema_path, 'r') as file:
                                existing_schema = json.loads(file.read())
                            if entrypoint_schema != existing_schema:
                                self._logger.warning(
                                    'Contract `%s` falsely claims to be a `%s`', contract_config.address, contract_config.typename
                                )

            elif isinstance(index_config, BigMapIndexConfig):
                for big_map_handler_config in index_config.handlers:
                    contract_config = big_map_handler_config.contract_config

                    contract_schemas = await self._get_schema(index_config.datasource_config, contract_config, False)

                    contract_schemas_path = join(schemas_path, contract_config.module_name)
                    mkdir_p(contract_schemas_path)
                    big_map_schemas_path = join(contract_schemas_path, 'big_map')
                    mkdir_p(big_map_schemas_path)

                    try:
                        big_map_schema = next(ep for ep in contract_schemas['bigMaps'] if ep['path'] == big_map_handler_config.path)
                    except StopIteration as e:
                        raise ConfigurationError(
                            f'Contract `{contract_config.address}` has no big map path `{big_map_handler_config.path}`'
                        ) from e
                    big_map_path = big_map_handler_config.path.replace('.', '_')
                    big_map_key_schema = big_map_schema['keySchema']
                    big_map_key_schema_path = join(big_map_schemas_path, f'{big_map_path}_key.json')
                    write(big_map_key_schema_path, json.dumps(big_map_key_schema, indent=4))

                    big_map_value_schema = big_map_schema['valueSchema']
                    big_map_value_schema_path = join(big_map_schemas_path, f'{big_map_path}_value.json')
                    write(big_map_value_schema_path, json.dumps(big_map_value_schema, indent=4))

            elif isinstance(index_config, HeadIndexConfig):
                pass

            elif isinstance(index_config, IndexTemplateConfig):
                raise ConfigInitializationException

            else:
                raise NotImplementedError(f'Index kind `{index_config.kind}` is not supported')

    async def generate_types(self, overwrite_types: bool = False) -> None:
        """Generate typeclasses from fetched JSONSchemas: contract's storage, parameter, big map keys/values."""
        schemas_path = join(self._config.package_path, 'schemas')
        types_path = join(self._config.package_path, 'types')

        self._logger.info('Creating `types` package')
        touch(join(types_path, '__init__.py'))

        for root, dirs, files in os.walk(schemas_path):
            types_root = root.replace(schemas_path, types_path)

            for dir in dirs:
                dir_path = join(types_root, dir)
                touch(join(dir_path, '__init__.py'))

            for file in files:
                name, ext = splitext(basename(file))
                if ext != '.json':
                    continue

                input_path = join(root, file)
                output_path = join(types_root, f'{pascal_to_snake(name)}.py')

                if exists(output_path) and not overwrite_types:
                    continue

                # NOTE: Skip if the first line starts with "# dipdup: ignore"
                if exists(output_path):
                    with open(output_path) as type_file:
                        first_line = type_file.readline()
                        if re.match(r'^#\s+dipdup:\s+ignore\s*', first_line):
                            self._logger.info('Skipping `%s`', output_path)
                            continue

                if name == 'storage':
                    name = '_'.join([root.split('/')[-1], name])
                if root.split('/')[-1] == 'parameter':
                    name += '_parameter'

                name = snake_to_pascal(name)
                self._logger.info('Generating type `%s`', name)
                args = [
                    'datamodel-codegen',
                    '--input',
                    input_path,
                    '--output',
                    output_path,
                    '--class-name',
                    name.lstrip('_'),
                    '--disable-timestamp',
                ]
                self._logger.debug(' '.join(args))
                subprocess.run(args, check=True)

    async def generate_handlers(self) -> None:
        """Generate handler stubs with typehints from templates if not exist"""
        handler_config: HandlerConfig
        for index_config in self._config.indexes.values():
            if isinstance(index_config, (OperationIndexConfig, BigMapIndexConfig, HeadIndexConfig)):
                for handler_config in index_config.handlers:
                    await self._generate_callback(handler_config)

            else:
                raise NotImplementedError(f'Index kind `{index_config.kind}` is not supported')

    async def generate_hooks(self) -> None:
        for hook_configs in self._config.hooks.values(), default_hooks.values():
            for hook_config in hook_configs:
                await self._generate_callback(hook_config, sql=True)

    async def generate_docker(self, image: str, tag: str, env_file: str) -> None:
        self._logger.info('Generating Docker template')
        docker_path = join(self._config.package_path, 'docker')
        mkdir_p(docker_path)

        dockerfile_template = load_template('docker/Dockerfile')
        docker_compose_template = load_template('docker/docker-compose.yml')
        dipdup_env_template = load_template('docker/dipdup.env')

        dockerfile_code = dockerfile_template.render(
            image=f'{image}:{tag}',
            package=self._config.package,
            package_path=self._config.package_path,
        )
        write(join(docker_path, 'Dockerfile'), dockerfile_code, overwrite=True)

        mounts = {}
        for path in self._config.paths:
            path_part = path.split("/")[-1]
            from_ = join(relpath(self._config.package_path, path), path_part)
            to = f'/home/dipdup/{path_part}'
            mounts[from_] = to

        command = []
        for path in self._config.paths:
            command += ['-c', path.split("/")[-1]]
        command += ['run']

        docker_compose_code = docker_compose_template.render(
            package=self._config.package,
            mounts=mounts,
            env_file=env_file,
            command=command,
        )
        write(join(docker_path, 'docker-compose.yml'), docker_compose_code, overwrite=True)

        dipdup_env_code = dipdup_env_template.render(
            environment={
                **DEFAULT_DOCKER_ENV_FILE_CONTENT,
                **self._config.environment,
            }
        )
        write(join(docker_path, 'dipdup.env.example'), dipdup_env_code, overwrite=True)
        write(join(docker_path, 'dipdup.env'), dipdup_env_code, overwrite=False)

        write(join(docker_path, '.gitignore'), '*.env')

    async def cleanup(self) -> None:
        """Remove fetched JSONSchemas"""
        self._logger.info('Cleaning up')
        schemas_path = join(self._config.package_path, 'schemas')
        rmtree(schemas_path)

    async def verify_package(self) -> None:
        import_submodules(self._config.package)

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
                try:
                    address = (await datasource.get_originated_contracts(address))[0]
                except IndexError as e:
                    raise ConfigurationError(f'No contracts were originated from `{address}`') from e
                self._logger.info('Fetching schemas for contract `%s` (originated from `%s`)', address, contract_config.address)
            else:
                self._logger.info('Fetching schemas for contract `%s`', address)

            address_schemas_json = await datasource.get_jsonschemas(address)
            self._schemas[datasource_config][address] = address_schemas_json
        return self._schemas[datasource_config][address]

    async def migrate_handlers_to_v10(self) -> None:
        remove_lines = [
            'from dipdup.models import',
            'from dipdup.context import',
            'from dipdup.utils import reindex',
        ]
        add_lines = [
            'from dipdup.models import OperationData, Transaction, Origination, BigMapDiff, BigMapData, BigMapAction',
            'from dipdup.context import HandlerContext, HookContext',
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

    async def migrate_handlers_to_v11(self) -> None:
        replace_table = {
            'BigMapAction.ADD': 'BigMapAction.ADD_KEY',
            'BigMapAction.UPDATE': 'BigMapAction.UPDATE_KEY',
            'BigMapAction.REMOVE': 'BigMapAction.REMOVE_KEY',
        }
        handlers_path = join(self._config.package_path, 'handlers')

        for root, _, files in os.walk(handlers_path):
            for filename in files:
                if filename == '__init__.py' or not filename.endswith('.py'):
                    continue
                path = join(root, filename)
                newfile = []
                with open(path) as file:
                    for line in file.read().split('\n'):
                        # Replace by table
                        for from_, to in replace_table.items():
                            line = line.replace(from_, to)
                        newfile.append(line)
                with open(path, 'w') as file:
                    file.write('\n'.join(newfile))

    async def _generate_callback(self, callback_config: CallbackMixin, sql: bool = False) -> None:
        subpackage_path = join(self._config.package_path, f'{callback_config.kind}s')

        original_callback = callback_config.callback
        subpackages = callback_config.callback.split('.')
        subpackages, callback = subpackages[:-1], subpackages[-1]
        subpackage_path = join(subpackage_path, *subpackages)

        init_path = join(subpackage_path, '__init__.py')
        touch(init_path)

        callback_path = join(subpackage_path, f'{callback}.py')
        if not exists(callback_path):
            self._logger.info('Generating %s callback `%s`', callback_config.kind, callback)
            callback_template = load_template('callback.py')

            arguments = callback_config.format_arguments()
            imports = set(callback_config.format_imports(self._config.package))

            code: List[str] = []
            if sql:
                code.append(f"await ctx.execute_sql('{original_callback}')")
                if callback == 'on_rollback':
                    imports.add('from dipdup.enums import ReindexingReason')
                    code.append('await ctx.reindex(ReindexingReason.ROLLBACK)')
            else:
                code.append('...')

            callback_code = callback_template.render(
                callback=callback,
                arguments=tuple(dict.fromkeys(arguments)),
                imports=tuple(dict.fromkeys(imports)),
                code=code,
            )
            write(callback_path, callback_code)

        if sql:
            # NOTE: Preserve the same structure as in `handlers`
            sql_path = join(self._config.package_path, 'sql', *subpackages, callback, '.keep')
            touch(sql_path)
