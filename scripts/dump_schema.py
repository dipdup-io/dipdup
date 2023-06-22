#!/usr/bin/env python3
from pathlib import Path
from dipdup.config import DipDupConfig
import orjson
from dc_schema import get_schema

schema_dict = get_schema(DipDupConfig)
schema_path = Path(__file__).parent.parent / 'schema.json'
schema_path.write_bytes(orjson.dumps(schema_dict, option=orjson.OPT_INDENT_2))
