#!/usr/bin/env python3
import subprocess
from pathlib import Path
from shutil import rmtree

from dipdup.project import answers_from_replay
from dipdup.project import render_project

projects_path = Path(__file__).parent.parent / 'projects'
demos_path = Path(__file__).parent.parent / 'src'


def _get_demos() -> list[Path]:
    return list(demos_path.iterdir())


def _get_projects() -> list[Path]:
    return list(projects_path.iterdir())


for demo_path in _get_demos():
    if not demo_path.name.startswith('demo_') or 'uniswap' in demo_path.name:
        continue
    if demo_path.is_dir():
        print(f'=> Removing `{demo_path.name}`')
        rmtree(demo_path, ignore_errors=True)
        rmtree(demo_path.parent / 'src' / demo_path.name, ignore_errors=True)

for project_path in _get_projects():
    if not project_path.name.endswith('.json'):
        continue

    print(f'=> Rendering {project_path.name}')
    answers = answers_from_replay(project_path)
    render_project(answers, force=True)

    package = answers['package']
    subprocess.run(['mv', package, 'src'], check=True)

    print(f'=> Initializing `{package}`')
    subprocess.run(
        ['dipdup', 'init', '--force'],
        cwd=Path(__file__).parent.parent / 'src' / package,
        check=True,
    )

    for env in ('dev', 'compose', 'swarm'):
        subprocess.run(
            [
                'dipdup',
                '-c',
                'dipdup.yml',
                '-c',
                f'config/{env}.yml',
                'config',
                'env',
                '-o',
                f'config/{env}.default.env',
            ],
            cwd=Path(__file__).parent.parent / 'src' / package,
            check=True,
        )
