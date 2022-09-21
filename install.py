#!python
import os
import subprocess
import sys
from functools import partial
from shutil import rmtree
from shutil import which
from typing import NoReturn

DEFAULT_REPO = 'https://github.com/dipdup-net/dipdup'
DEFAULT_REF = 'master'

run = partial(subprocess.run, check=True, shell=True)


class bcolors:
    OKBLUE = '\033[34m'
    OKGREEN = '\033[92m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'


def echo(msg: str, color: str = bcolors.OKBLUE) -> None:
    print(color + f'=> {msg}' + bcolors.ENDC)


def fail(msg: str) -> NoReturn:
    echo(msg, color=bcolors.FAIL)
    sys.exit(1)


def done(msg: str) -> NoReturn:
    echo(msg, color=bcolors.OKGREEN)
    sys.exit(0)


def main(
    quiet: bool = False,
    repo: str = DEFAULT_REPO,
    ref: str = DEFAULT_REF,
) -> None:
    if sys.version_info < (3, 10):
        fail('DipDup requires Python 3.10')

    echo('Welcome to DipDup installer')

    if not which('pipx'):
        echo('Installing pipx')
        run('pip install --user -q pipx')
        run('python -m pipx ensurepath')

    if not which('cookiecutter'):
        echo('Installing cookiecutter')
        run('pipx install cookiecutter')

    if not which('poetry'):
        echo('Installing poetry')
        run('pipx install poetry')

    cookiecutter_cmd = 'cookiecutter'
    if repo.startswith(('git@', 'https://')):
        echo('Using remote template')
        cookiecutter_cmd += f' -f {repo} -c {ref} --directory cookiecutter'
    else:
        echo('Using local template')
        cookiecutter_cmd += f' {repo}'
    if quiet:
        cookiecutter_cmd += ' --no-input'

    rmtree(os.path.expanduser('~/.cookiecutters/dipdup'), ignore_errors=True)
    run(cookiecutter_cmd)

    for _dir in os.listdir(os.getcwd()):
        if not os.path.isfile(f'{_dir}/dipdup.yml'):
            continue
        if os.path.isfile(f'{_dir}/poetry.lock'):
            continue

        echo(f'Found new project `{_dir}`')
        run('git init', cwd=_dir)

        echo('Running initial setup (can take a while)')
        run('make install', cwd=_dir)

        echo('Verifying project')
        run('make lint', cwd=_dir)

        done('Done! DipDup is ready to use.')

    fail('No new projects found')


if __name__ == '__main__':
    args = sys.argv[1:]
    quiet = False
    if '-q' in args:
        args.remove('-q')
        quiet = True

    if len(args) not in (0, 1, 2):
        fail('Usage: install.py [-q] [repo] [ref]')

    main(quiet, *args)
