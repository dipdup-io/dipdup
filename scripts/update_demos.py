#!/usr/bin/env python3
import subprocess
from pathlib import Path
from shutil import rmtree

from dipdup.project import BaseProject

demos_path = Path(__file__).parent.parent / 'demos'


def _get_demos() -> list[Path]:
    # FIXME
    # return list(demos_path.iterdir())
    return [
        Path('demos/demo-registrydao.json'),
        Path('demos/demo-registrydao'),
        Path('demos/demo-factories.json'),
        Path('demos/demo-factories'),
    ]


for demo in _get_demos():
    if demo.is_dir():
        rmtree(demo)

for demo in _get_demos():
    if not demo.name.endswith('.json'):
        continue

    print(f'Updating {demo.name}')
    project = BaseProject()
    project.run(quiet=True, replay=str(demo))
    project.render(force=True)

    project_name = project.answers['project_name']
    package = project.answers['package']
    subprocess.run(['mv', project_name, 'demos'], check=True)

for demo in _get_demos():
    if not demo.is_dir():
        continue

    print(f'Initializing {demo.name}')
    subprocess.run(
        ['dipdup', 'init', '--overwrite-types'],
        cwd=demo,
        check=True,
    )
