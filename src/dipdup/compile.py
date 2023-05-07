import subprocess
from pathlib import Path
from typing import Any

_venv = Path('.venv-nuitka')
_venv_site_packages = _venv / 'lib/python3.11/site-packages/'
_venv_pip = _venv / 'bin/pip'
_venv_python = _venv / 'bin/python'
_venv_dipdup = _venv / 'bin/dipdup'

_nuitka_args = (
    _venv_python,
    '-OO',
    '-m',
    'nuitka',
    '--clang',
    '--lto=yes',
    '--prefer-source-code',
    '--warn-implicit-exceptions',
    '--warn-unusual-code',
    '--user-package-configuration-file=web3.nuitka-package.config.yml',
)
_nuitka_src = '/usr/lib/python3.11/site-packages/nuitka/'


def srun(*args: Any) -> None:
    subprocess.run(args, check=True)


def create_venv() -> None:
    srun('python', '-m', 'venv', _venv)
    srun('cp', '-r', _nuitka_src, _venv_site_packages)
    srun(_venv_pip, 'install', '-U', 'pip', 'wheel', 'setuptools', 'ordered-set', 'pycryptodome')
    srun(_venv_pip, 'install', '.')


def compile_dipdup() -> None:
    create_venv()
    srun(*_nuitka_args, '--standalone', _venv_dipdup)
    srun('du', '-sh', 'dipdup.dist/')


def compile_project(name: str, site_packages: bool = False) -> None:
    create_venv()
    prefix = _venv_site_packages if site_packages else Path('src/')
    srun('rm', '-rf', f'dipdup.dist/{name}*')
    srun(
        *_nuitka_args,
        '--module',
        f'--include-package={name}',
        '--output-dir=dipdup.dist',
        f'{prefix}/{name}',
    )

    for file in Path(f'{prefix}/{name}/').glob('**/*.py'):
        if file.name == '__init__.py':
            file = file.parent

        srun(
            *_nuitka_args,
            '--module',
            f'--output-dir=dipdup.dist/{file.relative_to(prefix).parent}',
            file,
        )

    if not site_packages:
        for dir in ('abi', 'sql', 'graphql', 'hasura'):
            srun('cp', '-r', f'{prefix}/{name}/{dir}', f'dipdup.dist/{name}/')
