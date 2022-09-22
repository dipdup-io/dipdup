#!/usr/bin/env python3
from pathlib import Path
from os.path import join
from dipdup.codegen import questions
import json

path = join(Path(__file__).parent.parent, 'docs', 'cookiecutter.json')

defaults = {i['name']: i['default'] for i in questions}  # type: ignore
with open(path, 'w') as f:
    f.write(json.dumps(defaults, indent=4))
