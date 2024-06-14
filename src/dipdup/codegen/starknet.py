from functools import cache
from pathlib import Path
from typing import Any

import orjson
from Crypto.Hash import keccak
from starknet_py.abi.v2 import Abi  # type: ignore
from starknet_py.abi.v2 import AbiParser
from starknet_py.abi.v2 import AbiParsingError
from starknet_py.cairo.data_types import BoolType  # type: ignore
from starknet_py.cairo.data_types import CairoType
from starknet_py.cairo.data_types import EventType
from starknet_py.cairo.data_types import FeltType
from starknet_py.cairo.data_types import UintType
from starknet_py.serialization import serializer_for_event  # type: ignore

from dipdup.codegen import CodeGenerator
from dipdup.config import HandlerConfig
from dipdup.config.starknet_events import StarknetEventsIndexConfig
from dipdup.package import ConvertedCairoAbi
from dipdup.package import ConvertedEventCairoAbi
from dipdup.package import DipDupPackage
from dipdup.utils import json_dumps
from dipdup.utils import snake_to_pascal
from dipdup.utils import touch

# TODO: Support all types
_abi_type_map = {
    FeltType: 'integer',
    UintType: 'integer',
    BoolType: 'boolean',
}


def _convert_type(type_: CairoType) -> str:
    return _abi_type_map[type(type_)]


def _jsonschema_from_event(event: EventType) -> dict[str, Any]:
    # TODO: Unpack nested types (starknet.py could do that)
    return {
        '$schema': 'http://json-schema.org/draft/2019-09/schema#',
        'type': 'object',
        'properties': {key: {'type': _convert_type(value)} for key, value in event.types.items()},
        'required': tuple(event.types.keys()),
        'additionalProperties': False,
    }


def sn_keccak(x: str) -> str:
    # NOTE: Create keccak256 hash in bytes and return hex representation of the first 250 bits.
    keccak_hash = keccak.new(data=x.encode('ascii'), digest_bits=256).digest()
    return f'0x{int.from_bytes(keccak_hash, "big") & (1 << 248) - 1:x}'


@cache
def _loaded_abis(package: DipDupPackage) -> dict[str, Abi]:
    result = {}
    for abi_path in package.cairo_abi_paths:
        abi = orjson.loads(abi_path.read_bytes())

        try:
            parsed_abi = AbiParser(abi).parse()
        except AbiParsingError as e:
            raise e

        parsed_abi.events = {k.split('::')[-1]: v for k, v in parsed_abi.events.items()}
        result[abi_path.parent.stem] = parsed_abi
    return result


def convert_abi(package: DipDupPackage) -> dict[str, ConvertedCairoAbi]:
    abi_by_typename: dict[str, ConvertedCairoAbi] = {}

    for contract_typename, parsed_abi in _loaded_abis(package).items():
        converted_abi: ConvertedCairoAbi = {
            'events': {},
        }

        for name, event_type in parsed_abi.events.items():
            if name in converted_abi['events']:
                raise NotImplementedError('Multiple events with the same name are not supported')
            converted_abi['events'][name] = ConvertedEventCairoAbi(
                name=name,
                event_identifier=sn_keccak(name),
                members=event_type.types,
                serializer=serializer_for_event(event_type),
            )
        abi_by_typename[contract_typename] = converted_abi

    return abi_by_typename


def abi_to_jsonschemas(
    package: DipDupPackage,
    events: set[str],
) -> None:
    # load abi to json and then parse with starknet.py
    # select objects to generate types
    # convert types in to schema
    # write schema
    for contract_typename, parsed_abi in _loaded_abis(package).items():
        for event_name in events:
            if event_name not in parsed_abi.events:
                continue

            schema = _jsonschema_from_event(parsed_abi.events[event_name])
            schema_path = package.schemas / contract_typename / 'starknet_events' / f'{event_name}.json'
            touch(schema_path)
            schema_path.write_bytes(json_dumps(schema))


class StarknetCodeGenerator(CodeGenerator):
    # NOTE: For now ABIs need to be provided manually
    async def generate_abi(self) -> None: ...

    async def generate_schemas(self) -> None:
        self._cleanup_schemas()

        handler_config: HandlerConfig
        events: set[str] = set()

        for index_config in self._config.indexes.values():
            if isinstance(index_config, StarknetEventsIndexConfig):
                for handler_config in index_config.handlers:
                    events.add(handler_config.name)

        abi_to_jsonschemas(self._package, events)

    async def generate_hooks(self) -> None:
        pass

    async def generate_system_hooks(self) -> None:
        pass

    async def generate_handlers(self) -> None:
        pass

    def get_typeclass_name(self, schema_path: Path) -> str:
        module_name = schema_path.stem
        if schema_path.parent.name == 'starknet_events':
            class_name = f'{module_name}_payload'
        else:
            class_name = module_name
        return snake_to_pascal(class_name)

    async def _generate_type(self, schema_path: Path, force: bool) -> None:
        markers = {
            'starknet_events',
        }
        if not set(schema_path.parts).intersection(markers):
            return
        await super()._generate_type(schema_path, force)
