"""Everything about Python code generation (`dipdup init`)

* TzKT JSONSchema processing
* Callback codegen with Jinja2 templates
* Types codegen with datamodel-codegen

For `dipdup new` templates processing see `dipdup.project` module.

Please, keep imports lazy to speed up startup.
"""
import logging
import re
import subprocess
from pathlib import Path
from shutil import rmtree
from shutil import which
from typing import Any
from typing import Dict
from typing import List
from typing import cast

import orjson as json

from dipdup.config import BigMapIndexConfig
from dipdup.config import CallbackMixin
from dipdup.config import ContractConfig
from dipdup.config import DatasourceConfigT
from dipdup.config import DipDupConfig
from dipdup.config import EventIndexConfig
from dipdup.config import HeadIndexConfig
from dipdup.config import IndexTemplateConfig
from dipdup.config import OperationHandlerOriginationPatternConfig
from dipdup.config import OperationHandlerPatternConfigT
from dipdup.config import OperationHandlerTransactionPatternConfig
from dipdup.config import OperationIndexConfig
from dipdup.config import TokenTransferIndexConfig
from dipdup.config import TzktDatasourceConfig
from dipdup.config import UnknownEventHandlerConfig
from dipdup.config import event_hooks
from dipdup.datasources.datasource import Datasource
from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.exceptions import ConfigInitializationException
from dipdup.exceptions import ConfigurationError
from dipdup.exceptions import FeatureAvailabilityError
from dipdup.utils import import_submodules
from dipdup.utils import pascal_to_snake
from dipdup.utils import snake_to_pascal
from dipdup.utils.codegen import load_template
from dipdup.utils.codegen import touch
from dipdup.utils.codegen import write

KEEP_MARKER = '.keep'
PYTHON_MARKER = '__init__.py'
MODELS_MODULE = 'models.py'
CALLBACK_TEMPLATE = 'callback.py.j2'


def preprocess_storage_jsonschema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Preprocess `big_map` sections in JSONSchema.

    TzKT returns them as unions since before merging big map diffs there are just `int` pointers.
    We apply big map diffs to storage so there's no need to include `int` in type signature.
    """
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


class CodeGenerator:
    """Generates package based on config, invoked from `init` CLI command"""

    def __init__(self, config: DipDupConfig, datasources: Dict[DatasourceConfigT, Datasource]) -> None:
        self._logger = logging.getLogger('dipdup.codegen')
        self._config = config
        self._datasources = datasources
        self._schemas: Dict[TzktDatasourceConfig, Dict[str, Dict[str, Any]]] = {}

        self._path = Path(config.package_path)
        self._models_path = self._path / MODELS_MODULE
        self._schemas_path = self._path / 'schemas'
        self._types_path = self._path / 'types'
        self._handlers_path = self._path / 'handlers'
        self._hooks_path = self._path / 'hooks'
        self._sql_path = self._path / 'sql'
        self._graphql_path = self._path / 'graphql'

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

    async def create_package(self) -> None:
        """Create Python package skeleton if not exists"""
        touch(self._path / PYTHON_MARKER)
        touch(self._types_path / PYTHON_MARKER)
        touch(self._handlers_path / PYTHON_MARKER)
        touch(self._hooks_path / PYTHON_MARKER)
        touch(self._sql_path / KEEP_MARKER)
        touch(self._graphql_path / KEEP_MARKER)

        if not self._models_path.is_file():
            template = load_template('templates', f'{MODELS_MODULE}.j2')
            models_code = template.render()
            write(self._models_path, models_code)

    async def _fetch_operation_pattern_schema(
        self,
        operation_pattern_config: OperationHandlerPatternConfigT,
        datasource_config: TzktDatasourceConfig,
    ) -> None:
        if isinstance(operation_pattern_config, OperationHandlerTransactionPatternConfig) and operation_pattern_config.entrypoint:
            contract_config = operation_pattern_config.destination_contract_config
            originated = False
        elif isinstance(operation_pattern_config, OperationHandlerOriginationPatternConfig):
            contract_config = operation_pattern_config.contract_config
            originated = bool(operation_pattern_config.source)
        else:
            # NOTE: Operations without destination+entrypoint are untyped
            return

        self._logger.debug(contract_config)
        contract_schemas = await self._get_schema(datasource_config, contract_config, originated)

        contract_schemas_path = self._schemas_path / contract_config.module_name

        storage_schema_path = contract_schemas_path / 'storage.json'
        storage_schema = preprocess_storage_jsonschema(contract_schemas['storageSchema'])

        write(storage_schema_path, json.dumps(storage_schema, option=json.OPT_INDENT_2))

        if not isinstance(operation_pattern_config, OperationHandlerTransactionPatternConfig):
            return

        parameter_schemas_path = contract_schemas_path / 'parameter'
        entrypoint = cast(str, operation_pattern_config.entrypoint)

        try:
            entrypoint_schema = next(ep['parameterSchema'] for ep in contract_schemas['entrypoints'] if ep['name'] == entrypoint)
        except StopIteration as e:
            raise ConfigurationError(f'Contract `{contract_config.address}` has no entrypoint `{entrypoint}`') from e

        entrypoint = entrypoint.replace('.', '_').lstrip('_')
        entrypoint_schema_path = parameter_schemas_path / f'{entrypoint}.json'
        written = write(entrypoint_schema_path, json.dumps(entrypoint_schema, option=json.OPT_INDENT_2))
        if not written and contract_config.typename is not None:
            with open(entrypoint_schema_path, 'r') as file:
                existing_schema = json.loads(file.read())
            if entrypoint_schema != existing_schema:
                self._logger.warning('Contract `%s` falsely claims to be a `%s`', contract_config.address, contract_config.typename)

    async def _fetch_operation_index_schema(self, index_config: OperationIndexConfig) -> None:
        for handler_config in index_config.handlers:
            for operation_pattern_config in handler_config.pattern:
                await self._fetch_operation_pattern_schema(
                    operation_pattern_config,
                    index_config.datasource_config,
                )

    async def _fetch_big_map_index_schema(self, index_config: BigMapIndexConfig) -> None:
        for handler_config in index_config.handlers:
            contract_config = handler_config.contract_config

            contract_schemas = await self._get_schema(index_config.datasource_config, contract_config, False)

            contract_schemas_path = self._schemas_path / contract_config.module_name
            big_map_schemas_path = contract_schemas_path / 'big_map'

            try:
                big_map_schema = next(ep for ep in contract_schemas['bigMaps'] if ep['path'] == handler_config.path)
            except StopIteration as e:
                raise ConfigurationError(f'Contract `{contract_config.address}` has no big map path `{handler_config.path}`') from e
            big_map_path = handler_config.path.replace('.', '_')
            big_map_key_schema = big_map_schema['keySchema']
            big_map_key_schema_path = big_map_schemas_path / f'{big_map_path}_key.json'
            write(big_map_key_schema_path, json.dumps(big_map_key_schema, option=json.OPT_INDENT_2))

            big_map_value_schema = big_map_schema['valueSchema']
            big_map_value_schema_path = big_map_schemas_path / f'{big_map_path}_value.json'
            write(big_map_value_schema_path, json.dumps(big_map_value_schema, option=json.OPT_INDENT_2))

    async def _fetch_event_index_schema(self, index_config: EventIndexConfig) -> None:
        for handler_config in index_config.handlers:
            if isinstance(handler_config, UnknownEventHandlerConfig):
                continue

            contract_config = handler_config.contract_config
            contract_schemas = await self._get_schema(
                index_config.datasource_config,
                contract_config,
                False,
            )
            contract_schemas_path = self._schemas_path / contract_config.module_name
            event_schemas_path = contract_schemas_path / 'event'

            try:
                event_schema = next(ep for ep in contract_schemas['events'] if ep['tag'] == handler_config.tag)
            except StopIteration as e:
                raise ConfigurationError(f'Contract `{contract_config.address}` has no event with tag `{handler_config.tag}`') from e

            event_tag = handler_config.tag.replace('.', '_')
            event_schema = event_schema['eventSchema']
            event_schema_path = event_schemas_path / f'{event_tag}.json'
            write(event_schema_path, json.dumps(event_schema, option=json.OPT_INDENT_2))

    async def fetch_schemas(self) -> None:
        """Fetch JSONSchemas for all contracts used in config"""
        self._logger.info('Fetching contract schemas')

        for index_config in self._config.indexes.values():
            if isinstance(index_config, OperationIndexConfig):
                await self._fetch_operation_index_schema(index_config)
            elif isinstance(index_config, BigMapIndexConfig):
                await self._fetch_big_map_index_schema(index_config)
            elif isinstance(index_config, EventIndexConfig):
                await self._fetch_event_index_schema(index_config)
            elif isinstance(index_config, HeadIndexConfig):
                pass
            elif isinstance(index_config, TokenTransferIndexConfig):
                pass
            elif isinstance(index_config, IndexTemplateConfig):
                raise ConfigInitializationException
            else:
                raise NotImplementedError(f'Index kind `{index_config.kind}` is not supported')

    async def _generate_type(self, schema_path: Path, force: bool) -> None:
        rel_path = schema_path.relative_to(self._schemas_path)
        type_pkg_path = self._types_path / rel_path

        if schema_path.is_dir():
            touch(type_pkg_path / PYTHON_MARKER)
            return

        if not schema_path.name.endswith('.json'):
            self._logger.warning('Skipping `%s`: not a JSON', schema_path)
            return

        module_name = schema_path.stem
        output_path = type_pkg_path.parent / f'{pascal_to_snake(module_name)}.py'
        if output_path.exists() and not force:
            self._logger.info('Skipping `%s`: type already exists', schema_path)
            return

        # NOTE: Skip if the first line starts with "# dipdup: ignore"
        if output_path.exists():
            with open(output_path) as type_file:
                first_line = type_file.readline()
                if re.match(r'^#\s+dipdup:\s+ignore\s*', first_line):
                    self._logger.info('Skipping `%s`: "# dipdup: ignore" marker found', output_path)
                    return

        datamodel_codegen = which('datamodel-codegen')
        if not datamodel_codegen:
            raise FeatureAvailabilityError(
                feature='codegen',
                reason='datamodel-codegen is not installed. Are you in the `-slim` Docker image? If not - run `dipdup-install`.',
            )

        if schema_path.name == 'storage.json':
            class_name = f'{schema_path.parent.name}_storage'
        elif schema_path.parent.name == 'parameter':
            class_name = f'{module_name}_parameter'
        elif schema_path.parent.name == 'event':
            class_name = f'{module_name}_payload'
        else:
            class_name = module_name

        class_name = snake_to_pascal(class_name).lstrip('_')

        self._logger.info('Generating type `%s`', class_name)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        (output_path.parent / PYTHON_MARKER).touch(exist_ok=True)
        args = [
            datamodel_codegen,
            '--input',
            str(schema_path),
            '--output',
            str(output_path),
            '--class-name',
            class_name,
            '--disable-timestamp',
        ]
        self._logger.debug(' '.join(args))
        subprocess.run(args, check=True)

    async def generate_types(self, overwrite_types: bool = False) -> None:
        """Generate typeclasses from fetched JSONSchemas: contract's storage, parameters, big maps and events."""

        self._logger.info('Creating `types` package')
        touch(self._types_path / PYTHON_MARKER)

        for path in self._schemas_path.glob('**/*'):
            await self._generate_type(path, overwrite_types)

    async def generate_handlers(self) -> None:
        """Generate handler stubs with typehints from templates if not exist"""
        for index_config in self._config.indexes.values():
            if isinstance(index_config, IndexTemplateConfig):
                continue
            for handler_config in index_config.handlers:
                await self._generate_callback(handler_config)

    async def generate_hooks(self) -> None:
        for hook_configs in self._config.hooks.values(), event_hooks.values():
            for hook_config in hook_configs:
                await self._generate_callback(hook_config, sql=True)

    async def cleanup(self) -> None:
        """Remove fetched JSONSchemas"""
        self._logger.info('Cleaning up')
        rmtree(self._schemas_path, ignore_errors=True)

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

    async def _generate_callback(self, callback_config: CallbackMixin, sql: bool = False) -> None:
        original_callback = callback_config.callback
        subpackages = callback_config.callback.split('.')
        subpackages, callback = subpackages[:-1], subpackages[-1]

        callback_path = Path(
            self._path,
            f'{callback_config.kind}s',
            *subpackages,
            f'{callback}.py',
        )

        if not callback_path.exists():
            self._logger.info('Generating %s callback `%s`', callback_config.kind, callback)
            callback_template = load_template('templates', CALLBACK_TEMPLATE)

            arguments = callback_config.format_arguments()
            imports = set(callback_config.format_imports(self._config.package))

            code: List[str] = []
            if sql:
                code.append(f"await ctx.execute_sql('{original_callback}')")
                if callback == 'on_index_rollback':
                    code.append('await ctx.rollback(')
                    code.append('    index=index.name,')
                    code.append('    from_level=from_level,')
                    code.append('    to_level=to_level,')
                    code.append(')')
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
            sql_path = Path(
                self._sql_path,
                *subpackages,
                callback,
                KEEP_MARKER,
            )
            touch(sql_path)
