#!python
import os
import subprocess
import sys
from functools import partial
from os import environ as env
from os.path import join
from shutil import rmtree
from shutil import which
from tempfile import TemporaryDirectory
from typing import NoReturn

TEMPLATE = env.get('TEMPLATE', 'master')
TEMPLATE_REPOSITORY = 'https://github.com/dipdup-net/dipdup-py'
TEMPLATE_PATH = 'cookiecutter'
CACHED_TEMPLATE_PATH = join(env["HOME"], '.cookiecutters', 'dipdup-py')
CWD = os.getcwd()

run = partial(subprocess.run, check=True, shell=True)


class bcolors:
    OKBLUE = '\033[34m'
    OKGREEN = '\033[92m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'


def echo(msg: str, color: str = bcolors.OKBLUE) -> None:
    print(color + f'==> {msg}' + bcolors.ENDC)


def err(msg: str, color: str = bcolors.FAIL) -> None:
    print(color + msg + bcolors.ENDC)


def fail(msg: str) -> NoReturn:
    echo(msg, color=bcolors.FAIL)
    sys.exit(1)


echo(f'Installing DipDup from template `{TEMPLATE}`')

echo('Checking for dependencies')
for binary in ('git', 'make', 'poetry'):
    if not which(binary):
        fail(f'`{binary}` not found, install it and try again')

with TemporaryDirectory(prefix='dipdup-install-') as tmpdir:
    echo(f'Preparing `{tmpdir}` environment')

    run(f'python -m venv {tmpdir}', cwd=tmpdir)
    run('bin/python -m pip install -Uq pip cookiecutter', cwd=tmpdir)

    rmtree(CACHED_TEMPLATE_PATH, ignore_errors=True)
    run(f'{tmpdir}/bin/cookiecutter -f {TEMPLATE_REPOSITORY} -c {TEMPLATE} --directory {TEMPLATE_PATH}')

    for _dir in os.listdir(CWD):
        if not os.path.isfile(f'{_dir}/dipdup.yml'):
            continue
        if os.path.isfile(f'{_dir}/poetry.lock'):
            continue

        echo(f'Found new project `{_dir}`')
        run('git init', cwd=_dir)

        echo('Running initial setup (can take a while)')
        run('make install', cwd=_dir)

        echo(' Verifying project')
        run('make lint', cwd=_dir)

        break

echo('Done! DipDup is ready to use.', color=bcolors.OKGREEN)
