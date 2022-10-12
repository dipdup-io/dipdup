#!/usr/bin/env python3
from pathlib import Path

from dipdup.project import BaseProject

path = Path(__file__).parent.parent / 'docs' / 'cookiecutter.json'
project = BaseProject()
project.run(quiet=True, replay=None)
project.write_cookiecutter_json(path)
