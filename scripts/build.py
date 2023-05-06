import subprocess
from pathlib import Path
from typing import Any

_venv = Path('.venv-nuitka')
_venv_site_packages = _venv / 'lib/python3.11/site-packages/'
_venv_pip = _venv / 'bin/pip'
_venv_python = _venv / 'bin/python'
_venv_dipdup = _venv / 'bin/dipdup'
_nuitka_standalone = (
    _venv_python,
    '-m',
    'nuitka',
    '--clang',
    '--user-package-configuration-file=web3.nuitka-package.config.yml',
    '--standalone',
)
_nuitka_module = (
    _venv_python,
    '-m',
    'nuitka',
    '--clang',
    '--user-package-configuration-file=web3.nuitka-package.config.yml',
    '--module',
)
_nuitka_src = '/usr/lib/python3.11/site-packages/nuitka/'


def srun(*args: Any) -> None:
    subprocess.run(args, check=True)


def create_venv() -> None:
    srun('python', '-m', 'venv', _venv)
    srun('cp', '-r', _nuitka_src, _venv_site_packages)
    srun(_venv_pip, 'install', '-U', 'pip', 'wheel', 'setuptools', 'ordered-set', 'pycryptodome')
    srun(_venv_pip, 'install', '.')


def build_dipdup() -> None:
    srun(*_nuitka_standalone, _venv_dipdup)
    srun('du', '-sh', 'dipdup.dist/')


def build_project(name: str, site_packages: bool = False) -> None:
    prefix = _venv_site_packages if site_packages else Path('src/')
    srun('rm', '-rf', f'dipdup.dist/{name}*')
    srun(
        *_nuitka_module,
        f'--include-package={name}',
        '--output-dir=dipdup.dist',
        f'{prefix}/{name}',
    )

    for f in Path(f'{prefix}/{name}/').glob('**/*.py'):
        if f.name == '__init__.py':
            f = f.parent

        srun(
            *_nuitka_module,
            f'--output-dir=dipdup.dist/{f.relative_to(prefix).parent}',
            f,
        )

    if not site_packages:
        for dir in ('abi', 'sql', 'graphql', 'hasura'):
            srun('cp', '-r', f'{prefix}/{name}/{dir}', f'dipdup.dist/{name}/')


def build_eth_hash() -> None:
    build_project('eth_hash', site_packages=True)


import sys

args = sys.argv[1:]
if len(args) == 0:
    print('Usage: python dipdup_build.py create_venv|build_dipdup|build_project|missing_dirs')
elif args[0] == 'create_venv':
    create_venv()
elif args[0] == 'build_dipdup':
    build_dipdup()
elif args[0] == 'build_project':
    build_project(args[1])
elif args[0] == 'build_eth_hash':
    build_eth_hash()
else:
    print('Usage: python dipdup_build.py create_venv|build_dipdup|build_project|missing_dirs')
