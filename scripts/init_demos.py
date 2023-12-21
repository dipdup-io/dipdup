#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path

prefix = 'demo_'
projects_path = Path(__file__).parent.parent / 'projects'


def _get_projects() -> list[Path]:
    return list(projects_path.iterdir())


for path in _get_projects():
    package = path.name
    if not package.startswith(prefix):
        continue
    print(f'=> Initializing `{package}`')
    package_path = Path(__file__).parent.parent / 'src' / package
    subprocess.run(
        [
            'dipdup',
            'init',
            # '--force',
        ],
        cwd=package_path,
        check=True,
        env={
            **dict(os.environ),
            'STACK': '',
            'POSTGRES_PASSWORD': '',
            'HASURA_SECRET': '',
        },
    )
    Path(package_path).joinpath(package).unlink()
