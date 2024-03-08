from pathlib import Path
from typing import Any
from typing import cast

import eth_utils
import orjson
from web3 import Web3

from dipdup.codegen import CodeGenerator
from dipdup.config import AbiDatasourceConfig
from dipdup.config import HandlerConfig
from dipdup.config import SubsquidIndexConfigU
from dipdup.config.evm import EvmContractConfig
from dipdup.config.evm_subsquid import SubsquidIndexConfig
from dipdup.config.evm_subsquid_events import SubsquidEventsHandlerConfig
from dipdup.config.evm_subsquid_events import SubsquidEventsIndexConfig
from dipdup.config.evm_subsquid_traces import SubsquidTracesHandlerConfig
from dipdup.config.evm_subsquid_traces import SubsquidTracesIndexConfig
from dipdup.config.evm_subsquid_transactions import SubsquidTransactionsHandlerConfig
from dipdup.config.evm_subsquid_transactions import SubsquidTransactionsIndexConfig
from dipdup.datasources import AbiDatasource
from dipdup.exceptions import AbiNotAvailableError
from dipdup.exceptions import ConfigurationError
from dipdup.exceptions import DatasourceError
from dipdup.exceptions import FrameworkException
from dipdup.package import ConvertedAbi
from dipdup.package import ConvertedEventAbi
from dipdup.package import ConvertedMethodAbi
from dipdup.package import DipDupPackage
from dipdup.utils import json_dumps
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


def convert_abi(package: DipDupPackage) -> dict[str, ConvertedAbi]:
    abi_by_typename: dict[str, ConvertedAbi] = {}

    for abi_path in package.abi.glob('**/abi.json'):
        abi = orjson.loads(abi_path.read_bytes())
        converted_abi: ConvertedAbi = {
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
                    topic0=topic_from_abi(abi_item),
                    inputs=inputs,
                )
        abi_by_typename[abi_path.parent.stem] = converted_abi

    return abi_by_typename


def abi_to_jsonschemas(
    package: DipDupPackage,
    events: set[str],
    methods: set[str],
) -> None:
    for abi_path in package.abi.glob('**/abi.json'):
        abi = orjson.loads(abi_path.read_bytes())

        for abi_item in abi:
            if abi_item['type'] == 'function':
                name = abi_item['name']
                if name not in methods:
                    continue
                schema = jsonschema_from_abi(abi_item)
                schema_path = package.schemas / abi_path.parent.stem / 'evm_methods' / f'{name}.json'
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
        raise FrameworkException(f'`{abi_item["name"]}` is not a function; can\'t get sighash')

    signature = f'{abi_item["name"]}({",".join([i["type"] for i in abi_item["inputs"]])})'
    return Web3.keccak(text=signature).hex()[:10]


def topic_from_abi(event: dict[str, Any]) -> str:
    if event.get('type') != 'event':
        raise FrameworkException(f'`{event["name"]}` is not an event')

    signature = f'{event["name"]}({",".join([i["type"] for i in event["inputs"]])})'
    return '0x' + eth_utils.crypto.keccak(text=signature).hex()


class SubsquidCodeGenerator(CodeGenerator):
    async def generate_abi(self) -> None:
        for index_config in self._config.indexes.values():
            if isinstance(index_config, SubsquidIndexConfig):
                await self._fetch_abi(index_config)

    async def generate_schemas(self) -> None:
        self._cleanup_schemas()

        handler_config: HandlerConfig
        events: set[str] = set()
        methods: set[str] = set()

        for index_config in self._config.indexes.values():
            if isinstance(index_config, SubsquidEventsIndexConfig):
                for handler_config in index_config.handlers:
                    events.add(handler_config.name)
            elif isinstance(index_config, SubsquidTracesIndexConfig):
                raise NotImplementedError
            elif isinstance(index_config, SubsquidTransactionsIndexConfig):
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

    async def _fetch_abi(self, index_config: SubsquidIndexConfigU) -> None:
        if isinstance(index_config.abi, tuple):
            datasource_configs = index_config.abi
        elif index_config.abi:
            datasource_configs = (index_config.abi,)
        else:
            datasource_configs = self._config.abi_datasources

        contract: EvmContractConfig | None = None

        for handler_config in index_config.handlers:
            if isinstance(handler_config, SubsquidEventsHandlerConfig):
                contract = handler_config.contract
            elif isinstance(handler_config, SubsquidTracesHandlerConfig):
                raise NotImplementedError
            elif isinstance(handler_config, SubsquidTransactionsHandlerConfig):
                contract = handler_config.typed_contract

            if not contract:
                continue

            abi_path = self._package.abi / contract.module_name / 'abi.json'
            if abi_path.exists():
                continue

            address = contract.address or contract.abi
            if not address:
                raise ConfigurationError(f'`address` or `abi` must be specified for contract `{contract.module_name}`')

            for datasource_config in datasource_configs:
                # NOTE: Pydantic won't catch this cause we resolve datasource aliases after validation.
                if not isinstance(datasource_config, AbiDatasourceConfig):
                    raise ConfigurationError('`abi` must be a list of ABI datasources')

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
        return schema_path.stem

    async def _generate_type(self, schema_path: Path, force: bool) -> None:
        markers = {
            'evm_events',
            'evm_methods',
        }
        if not set(schema_path.parts).intersection(markers):
            return
        await super()._generate_type(schema_path, force)
