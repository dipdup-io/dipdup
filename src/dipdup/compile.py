import subprocess
from pathlib import Path
from typing import Any
from typing import TypedDict


class CompileOptions(TypedDict, total=False):
    venv_path: Path
    venv_site_packages: Path
    venv_pip: Path
    venv_python: Path
    venv_dipdup: Path
    nuitka_args: tuple[str, ...]
    nuitka_src: str


# NOTE: For now just my localhost config: py311, venv in-place, nuitka from AUR. Modify with key=value cli args.
DEFAULT_COMPILE_OPTIONS = CompileOptions(
    venv_path=Path('.venv-nuitka'),
    venv_site_packages=Path('.venv-nuitka/lib/python3.11/site-packages/'),
    venv_pip=Path('.venv-nuitka/bin/pip'),
    venv_python=Path('.venv-nuitka/bin/python'),
    venv_dipdup=Path('.venv-nuitka/bin/dipdup'),
    nuitka_args=(
        '.venv-nuitka/bin/python',
        '-OO',
        '-m',
        'nuitka',
        '--clang',
        '--lto=yes',
        '--prefer-source-code',
        '--warn-implicit-exceptions',
        '--warn-unusual-code',
        '--user-package-configuration-file=web3.nuitka-package.config.yml',
    ),
    nuitka_src='/usr/lib/python3.11/site-packages/nuitka/',
)


def srun(*args: Any) -> None:
    """naughty boi"""
    subprocess.run(args, check=True)


def create_venv(opts: CompileOptions) -> None:
    srun('python', '-m', 'venv', opts['venv_path'])
    srun('cp', '-r', opts['nuitka_src'], opts['venv_site_packages'])
    srun(opts['venv_pip'], 'install', '-U', 'pip', 'wheel', 'setuptools', 'ordered-set', 'pycryptodome')
    srun(opts['venv_pip'], 'install', '.')


def compile_dipdup(opts: CompileOptions) -> None:
    create_venv(opts)
    srun(*opts['nuitka_args'], '--standalone', opts['venv_dipdup'])
    srun('du', '-sh', 'dipdup.dist/')


def compile_project(name: str, opts: CompileOptions, site_packages: bool = False) -> None:
    create_venv(opts)
    prefix = opts['venv_site_packages'] if site_packages else Path('src/')
    srun('rm', '-rf', f'dipdup.dist/{name}*')
    srun(
        *opts['nuitka_args'],
        '--module',
        f'--include-package={name}',
        '--output-dir=dipdup.dist',
        f'{prefix}/{name}',
    )

    for file in Path(f'{prefix}/{name}/').glob('**/*.py'):
        if file.name == '__init__.py':
            file = file.parent

        srun(
            *opts['nuitka_args'],
            '--module',
            f'--output-dir=dipdup.dist/{file.relative_to(prefix).parent}',
            file,
        )

    if not site_packages:
        for dir in ('abi', 'sql', 'graphql', 'hasura'):
            srun('cp', '-r', f'{prefix}/{name}/{dir}', f'dipdup.dist/{name}/')
