#!/usr/bin/env python3
import subprocess
from copy import copy
from pathlib import Path
from shutil import rmtree

from dipdup.project import DEFAULT_ANSWERS
from dipdup.project import render_project

projects_path = Path(__file__).parent.parent / 'projects'
demos_path = Path(__file__).parent.parent / 'src'


def _get_demos() -> list[Path]:
    return list(demos_path.iterdir())


def _get_projects() -> list[Path]:
    return list(projects_path.iterdir())


for path in _get_demos():
    if not path.name.startswith('demo_'):
        continue
    if path.is_dir():
        print(f'=> Removing `{path.name}`')
        rmtree(path, ignore_errors=True)
        rmtree(path.parent / 'src' / path.name, ignore_errors=True)

for path in _get_projects():
    package = path.name
    if not package.startswith('demo_'):
        continue

    print(f'=> Rendering {path}')
    answers = copy(DEFAULT_ANSWERS)
    answers['package'] = package
    answers['template'] = package

    render_project(answers, force=True)

    subprocess.run(['mv', package, 'src'], check=True)
