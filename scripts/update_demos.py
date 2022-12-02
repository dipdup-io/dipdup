#!/usr/bin/env python3
import subprocess
from pathlib import Path
from shutil import rmtree

from dipdup.project import BaseProject

demos_path = Path(__file__).parent.parent / 'demos'

for demo in list(demos_path.iterdir()):
    if demo.is_dir():
        rmtree(demo)

for demo in list(demos_path.iterdir()):
    if not demo.name.endswith('.json'):
        continue

    print(f'Updating {demo.name}')
    project = BaseProject()
    project.run(quiet=True, replay=str(demo))
    project.render(force=True)

    project_name = project.answers['project_name']
    package = project.answers['package']
    subprocess.run(['mv', project_name, 'demos'], check=True)

for demo in list(demos_path.iterdir()):
    if not demo.is_dir():
        continue

    print(f'Initializing {demo.name}')
    subprocess.run(
        ['dipdup', 'init', '--overwrite-types'],
        cwd=demo,
        check=True,
    )
