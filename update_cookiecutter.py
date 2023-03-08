#!/usr/bin/env python3
from pathlib import Path

from dipdup.project import BaseProject

path = Path(__file__).parent.parent / 'docs' / 'cookiecutter.json'
project = BaseProject()  # type: ignore[call-arg]
project.run(quiet=True, replay=None)
project.write_cookiecutter_json(path)
