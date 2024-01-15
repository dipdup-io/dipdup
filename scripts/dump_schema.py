#!/usr/bin/env python3
# NOTE: Run `pdm add -G dev -e ../dc_schema` first.
from pathlib import Path

import orjson
from dc_schema import get_schema  # type: ignore[import-not-found]

from dipdup.config import DipDupConfig

schema_dict = get_schema(DipDupConfig)

# NOTE: EVM addresses correctly parsed by Pydantic even if specified as integers
schema_dict['$defs']['EvmContractConfig']['properties']['address'] = {
    'anyOf': [
        {'type': 'integer'},
        {'type': 'string'},
    ]
}

# NOTE: Environment configs don't have package/spec_version fields, but can't be loaded directly anyway.
schema_dict['required'] = []

schema_path = Path(__file__).parent.parent / 'schema.json'
schema_path.write_bytes(orjson.dumps(schema_dict, option=orjson.OPT_INDENT_2))
