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
    if not path.name.startswith('demo_') or 'uniswap' in path.name:
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

    print(f'=> Initializing `{package}`')
    package_path = Path(__file__).parent.parent / 'src' / package
    subprocess.run(
        [
            'dipdup',
            'init',
            '--force',
        ],
        cwd=package_path,
        check=True,
    )

    configs_path = package_path / 'config'
    for config_path in configs_path.iterdir():
        subprocess.run(
            [
                'dipdup',
                '-c',
                'dipdup.yml',
                '-c',
                f'config/{config_path.stem}.yml',
                'config',
                'env',
                '-o',
                f'config/{config_path.stem}.default.env',
            ],
            cwd=package_path,
            check=True,
        )
