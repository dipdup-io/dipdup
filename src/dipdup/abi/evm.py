from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import TypedDict

import orjson

from dipdup.exceptions import FrameworkException
from dipdup.utils import json_dumps
from dipdup.utils import touch

if TYPE_CHECKING:
    from dipdup.package import DipDupPackage

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


class ConvertedEventAbi(TypedDict):
    name: str
    topic0: str
    inputs: tuple[tuple[str, bool], ...]
    topic_count: int


class ConvertedMethodAbi(TypedDict):
    name: str
    sighash: str
    inputs: tuple[dict[str, str], ...]
    outputs: tuple[dict[str, str], ...]


class ConvertedEvmAbi(TypedDict):
    events: dict[str, ConvertedEventAbi]
    methods: dict[str, ConvertedMethodAbi]


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
                # if name in converted_abi['methods']:
                #     raise NotImplementedError('Multiple methods with the same name are not supported')
                converted_abi['methods'][name] = ConvertedMethodAbi(
                    name=name,
                    sighash=sighash_from_abi(abi_item),
                    inputs=abi_item['inputs'],
                    outputs=abi_item['outputs'],
                )
            elif abi_item['type'] == 'event':
                name = abi_item['name']
                # if name in converted_abi['events']:
                #     raise NotImplementedError('Multiple events with the same name are not supported')
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
    from web3 import Web3

    if abi_item.get('type') != 'function':
        raise FrameworkException(f"`{abi_item['name']}` is not a function; can't get sighash")

    signature = f'{abi_item["name"]}({",".join([i["type"] for i in abi_item["inputs"]])})'
    return Web3.keccak(text=signature).hex()[:10]


def topic0_from_abi(event: dict[str, Any]) -> str:
    import eth_utils

    if event.get('type') != 'event':
        raise FrameworkException(f'`{event["name"]}` is not an event')

    signature = f'{event["name"]}({",".join([i["type"] for i in event["inputs"]])})'
    return '0x' + eth_utils.crypto.keccak(text=signature).hex()
