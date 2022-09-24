#!/usr/bin/env python3
from os.path import join
from pathlib import Path

from dipdup.project import DefaultProject

path = join(Path(__file__).parent.parent, 'docs', 'cookiecutter.json')
project = DefaultProject()
project.run(quiet=True)
project.write_cookiecutter_json(path)
