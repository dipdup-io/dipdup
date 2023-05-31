#!/usr/bin/env python3
from pathlib import Path

from dipdup.project import write_cookiecutter_json

path = Path(__file__).parent.parent / 'docs' / 'cookiecutter.json'
write_cookiecutter_json(path)
