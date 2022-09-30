#!/usr/bin/env python3
from os.path import join
from pathlib import Path

from dipdup.project import BaseProject

path = join(Path(__file__).parent.parent, 'docs', 'cookiecutter.json')
project = BaseProject()
project.run(quiet=True, replay=None)
project.write_cookiecutter_json(path)
