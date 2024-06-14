from pathlib import Path
from typing import Any
from typing import cast

import eth_utils
import orjson
from web3 import Web3

from dipdup.codegen import CodeGenerator
from dipdup.config import EvmIndexConfigU
from dipdup.config import HandlerConfig
from dipdup.config.abi_etherscan import AbiEtherscanDatasourceConfig
from dipdup.config.evm import EvmContractConfig
from dipdup.config.evm import EvmIndexConfig
from dipdup.config.evm_events import EvmEventsHandlerConfig
from dipdup.config.evm_events import EvmEventsIndexConfig
from dipdup.config.evm_transactions import EvmTransactionsHandlerConfig
from dipdup.config.evm_transactions import EvmTransactionsIndexConfig
from dipdup.datasources import AbiDatasource
from dipdup.exceptions import AbiNotAvailableError
from dipdup.exceptions import ConfigurationError
from dipdup.exceptions import DatasourceError
from dipdup.exceptions import FrameworkException
from dipdup.package import ConvertedEventAbi
from dipdup.package import ConvertedEvmAbi
from dipdup.package import ConvertedMethodAbi
from dipdup.package import DipDupPackage
from dipdup.utils import json_dumps
from dipdup.utils import snake_to_pascal
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


def convert_abi(package: DipDupPackage) -> dict[str, ConvertedEvmAbi]:
    abi_by_typename: dict[str, ConvertedEvmAbi] = {}

    for abi_path in package.evm_abi_paths:
        abi = orjson.loads(abi_path.read_bytes())
        converted_abi: ConvertedEvmAbi = {
            'events': {},
            'methods': {},
        }

        for abi_item in abi:
            if abi_item['type'] == 'function':
                name = abi_item['name']
                if name in converted_abi['methods']:
                    raise NotImplementedError('Multiple methods with the same name are not supported')
                converted_abi['methods'][name] = ConvertedMethodAbi(
                    name=name,
                    sighash=sighash_from_abi(abi_item),
                    inputs=abi_item['inputs'],
                    outputs=abi_item['outputs'],
                )
            elif abi_item['type'] == 'event':
                name = abi_item['name']
                if name in converted_abi['events']:
                    raise NotImplementedError('Multiple events with the same name are not supported')
                inputs = tuple((i['type'], i['indexed']) for i in abi_item['inputs'])
                converted_abi['events'][name] = ConvertedEventAbi(
                    name=name,
                    topic0=topic0_from_abi(abi_item),
                    inputs=inputs,
                    topic_count=len([i for i in inputs if i[1]]),
                )
        abi_by_typename[abi_path.parent.stem] = converted_abi

    return abi_by_typename


def abi_to_jsonschemas(
    package: DipDupPackage,
    events: set[str],
    methods: set[str],
) -> None:
    # NOTE: path used only for contract name receiving, indicating design problem
    for abi_path in package.evm_abi_paths:
        abi = orjson.loads(abi_path.read_bytes())

        for abi_item in abi:
            if abi_item['type'] == 'function':
                name = abi_item['name']
                if name not in methods:
                    continue
                schema = jsonschema_from_abi(abi_item)
                schema_path = package.schemas / abi_path.parent.stem / 'evm_transactions' / f'{name}.json'
            elif abi_item['type'] == 'event':
                name = abi_item['name']
                if name not in events:
                    continue
                schema = jsonschema_from_abi(abi_item)
                schema_path = package.schemas / abi_path.parent.stem / 'evm_events' / f'{name}.json'
            else:
                continue

            touch(schema_path)
            schema_path.write_bytes(json_dumps(schema))


def sighash_from_abi(abi_item: dict[str, Any]) -> str:
    if abi_item.get('type') != 'function':
        raise FrameworkException(f"`{abi_item['name']}` is not a function; can't get sighash")

    signature = f'{abi_item["name"]}({",".join([i["type"] for i in abi_item["inputs"]])})'
    return Web3.keccak(text=signature).hex()[:10]


def topic0_from_abi(event: dict[str, Any]) -> str:
    if event.get('type') != 'event':
        raise FrameworkException(f'`{event["name"]}` is not an event')

    signature = f'{event["name"]}({",".join([i["type"] for i in event["inputs"]])})'
    return '0x' + eth_utils.crypto.keccak(text=signature).hex()


class EvmCodeGenerator(CodeGenerator):
    async def generate_abi(self) -> None:
        for index_config in self._config.indexes.values():
            if isinstance(index_config, EvmIndexConfig):
                await self._fetch_abi(index_config)

    async def generate_schemas(self) -> None:
        self._cleanup_schemas()

        handler_config: HandlerConfig
        events: set[str] = set()
        methods: set[str] = set()

        for index_config in self._config.indexes.values():
            if isinstance(index_config, EvmEventsIndexConfig):
                for handler_config in index_config.handlers:
                    events.add(handler_config.name)
            elif isinstance(index_config, EvmTransactionsIndexConfig):
                for handler_config in index_config.handlers:
                    if handler_config.method:
                        methods.add(handler_config.method)

        abi_to_jsonschemas(self._package, events, methods)

    async def generate_hooks(self) -> None:
        pass

    async def generate_system_hooks(self) -> None:
        pass

    async def generate_handlers(self) -> None:
        pass

    async def _fetch_abi(self, index_config: EvmIndexConfigU) -> None:
        datasource_configs = tuple(c for c in index_config.datasources if isinstance(c, AbiEtherscanDatasourceConfig))

        contract: EvmContractConfig | None = None

        for handler_config in index_config.handlers:
            if isinstance(handler_config, EvmEventsHandlerConfig):
                contract = handler_config.contract
            elif isinstance(handler_config, EvmTransactionsHandlerConfig):
                contract = handler_config.typed_contract

            if not contract:
                continue

            abi_path = self._package.abi / contract.module_name / 'abi.json'
            if abi_path.exists():
                continue
            if not datasource_configs:
                raise ConfigurationError('No EVM ABI datasources found')

            address = contract.address or contract.abi
            if not address:
                raise ConfigurationError(f'`address` or `abi` must be specified for contract `{contract.module_name}`')

            for datasource_config in datasource_configs:

                datasource = cast(AbiDatasource[Any], self._datasources[datasource_config.name])
                try:
                    abi_json = await datasource.get_abi(address)
                    break
                except DatasourceError as e:
                    self._logger.warning('Failed to fetch ABI from `%s`: %s', datasource_config.name, e)
            else:
                raise AbiNotAvailableError(
                    address=address,
                    typename=contract.module_name,
                )

            touch(abi_path)
            abi_path.write_bytes(json_dumps(abi_json))

    def get_typeclass_name(self, schema_path: Path) -> str:
        module_name = schema_path.stem
        if schema_path.parent.name == 'evm_events':
            class_name = f'{module_name}_payload'
        elif schema_path.parent.name == 'evm_transactions':
            class_name = f'{module_name}_input'
        else:
            class_name = module_name
        return snake_to_pascal(class_name)

    async def _generate_type(self, schema_path: Path, force: bool) -> None:
        markers = {
            'evm_events',
            'evm_transactions',
        }
        if not set(schema_path.parts).intersection(markers):
            return
        await super()._generate_type(schema_path, force)
