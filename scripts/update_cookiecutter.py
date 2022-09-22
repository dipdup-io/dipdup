#!/usr/bin/env python3
import json
from os.path import join
from pathlib import Path

from dipdup.codegen import questions

path = join(Path(__file__).parent.parent, 'docs', 'cookiecutter.json')

defaults = {i['name']: i['default'] for i in questions}  # type: ignore
with open(path, 'w') as f:
    f.write(json.dumps(defaults, indent=4))
