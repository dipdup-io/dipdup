from pathlib import Path
from typing import Any
from typing import cast

import orjson

from dipdup.codegen import CodeGenerator
from dipdup.config import AbiDatasourceConfig
from dipdup.config.evm_subsquid_events import SubsquidEventsIndexConfig
from dipdup.config.evm_subsquid_operations import SubsquidOperationsIndexConfig
from dipdup.datasources import AbiDatasource
from dipdup.exceptions import ConfigurationError
from dipdup.exceptions import FrameworkException
from dipdup.package import PYTHON_MARKER
from dipdup.utils import touch

_abi_type_map: dict[str, str] = {
    'int': 'integer',
    'uint': 'integer',
    'address': 'string',
    'fixed': 'number',
    'ufixed': 'number',
    'bytes': 'string',
    'bool': 'boolean',
    'string': 'string',
    # TODO: arrays and tuples
    # https://docs.soliditylang.org/en/develop/abi-spec.html#types
    'tuple': 'object',
}


def _convert_type(abi_type: str) -> str:
    if abi_type in _abi_type_map:
        return _abi_type_map[abi_type]
    for k, v in _abi_type_map.items():
        if abi_type.startswith(k):
            return v
    raise FrameworkException(f'`{abi_type}` ABI type is not supported')


def _convert_name(name: str) -> str:
    return name.lstrip('_')


def jsonschema_from_abi(abi: dict[str, Any]) -> dict[str, Any]:
    return {
        '$schema': 'http://json-schema.org/draft/2019-09/schema#',
        'type': 'object',
        'properties': {_convert_name(i['name']): {'type': _convert_type(i['type'])} for i in abi['inputs']},
        'required': [_convert_name(i['name']) for i in abi['inputs']],
        'additionalProperties': False,
    }


class SubsquidCodeGenerator(CodeGenerator):
    async def generate_abi(self) -> None:
        for index_config in self._config.indexes.values():
            if isinstance(index_config, SubsquidEventsIndexConfig):
                await self._fetch_abi(index_config)
            elif isinstance(index_config, SubsquidOperationsIndexConfig):
                raise NotImplementedError

    async def generate_schemas(self) -> None:
        await self._convert_abi()

    # FIXME: tzkt copypaste
    async def generate_types(self, force: bool = False) -> None:
        """Generate typeclasses from fetched JSONSchemas: contract's storage, parameters, big maps and events."""

        self._logger.info('Creating `types` package')
        touch(self._package.types / PYTHON_MARKER)

        for path in self._package.schemas.glob('**/*.json'):
            await self._generate_type(path, force)

    async def generate_hooks(self) -> None:
        ...

    async def generate_event_hooks(self) -> None:
        ...

    async def generate_handlers(self) -> None:
        ...

    async def _fetch_abi(self, index_config: SubsquidEventsIndexConfig) -> None:
        datasource_configs = index_config.abi or self._config.abi_datasources

        for handler_config in index_config.handlers:
            abi_path = self._package.abi / f'{handler_config.contract.module_name}.json'
            if abi_path.exists():
                continue

            address = handler_config.contract.address

            for datasource_config in datasource_configs:
                if not isinstance(datasource_config, AbiDatasourceConfig):
                    raise ConfigurationError('`abi` must be a list of ABI datasources')

                datasource = cast(AbiDatasource[Any], self._datasources[datasource_config.name])
                abi_json = await datasource.get_abi(address)
                if abi_json:
                    break
            else:
                raise ConfigurationError(f'ABI for contract `{address}` not found')

            abi_path.touch()
            abi_path.write_bytes(orjson.dumps(abi_json, option=orjson.OPT_INDENT_2))

    async def _convert_abi(self) -> None:
        for path in self._package.abi.glob('**/*.json'):
            abi = orjson.loads(path.read_bytes())
            for item in abi:
                if item['type'] == 'function':
                    schema = jsonschema_from_abi(item)
                    schema_path = self._package.schemas / path.stem / 'evm_functions' / f'{item["name"]}.json'
                elif item['type'] == 'event':
                    schema = jsonschema_from_abi(item)
                    schema_path = self._package.schemas / path.stem / 'evm_events' / f'{item["name"]}.json'
                else:
                    continue

                touch(schema_path)
                schema_path.write_bytes(orjson.dumps(schema, option=orjson.OPT_INDENT_2))

    def get_typeclass_name(self, schema_path: Path) -> str:
        module_name = schema_path.stem
        # if schema_path.parent.name == 'evm_events':
        #     class_name = f'{module_name}_event'
        # elif schema_path.parent.name == 'evm_functions':
        #     class_name = f'{module_name}_function'
        # else:
        #     class_name = module_name
        return module_name
