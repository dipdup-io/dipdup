#!/usr/bin/env python3
import subprocess
from pathlib import Path
from shutil import rmtree

from dipdup.project import BaseProject

projects_path = Path(__file__).parent.parent / 'projects'
demos_path = Path(__file__).parent.parent / 'demos'


def _get_demos() -> list[Path]:
    return list(demos_path.iterdir())


def _get_projects() -> list[Path]:
    return list(projects_path.iterdir())


for demo_path in _get_demos():
    if demo_path.is_dir():
        print(f'=> Removing `{demo_path.name}`')
        rmtree(demo_path, ignore_errors=True)
        rmtree(demo_path.parent / 'src' / demo_path.name, ignore_errors=True)

for project_path in _get_projects():
    if not project_path.name.endswith('.json'):
        continue

    print(f'=> Rendering {project_path.name}')
    project = BaseProject()
    project.run(quiet=True, replay=str(project_path))
    project.render(force=True)

    project_name = project.answers['project_name']
    package = project.answers['package']
    subprocess.run(['mv', project_name, 'demos'], check=True)

    print(f'=> Linking `{project_name}`')
    subprocess.run(
        ['ln', '-sf', f'../demos/{project_name}/src/{package}', package],
        cwd=Path(__file__).parent.parent / 'src',
        check=True,
    )

    print(f'=> Initializing `{project_name}`')
    subprocess.run(
        ['dipdup', 'init', '--overwrite-types'],
        cwd=Path(__file__).parent.parent / 'demos' / project_name,
        check=True,
    )
