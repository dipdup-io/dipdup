import subprocess
import sys
from shutil import which
from typing import NoReturn

DEFAULT_REPO = 'https://github.com/dipdup-net/dipdup'
DEFAULT_REF = 'master'

def run(*args, **kwargs):
    return subprocess.run(*args, **kwargs, check=True, shell=True,)


class colors:
    BLUE = '\033[34m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'


def echo(msg: str, color: str = colors.BLUE) -> None:
    print(color + f'=> {msg}' + colors.ENDC)


def fail(msg: str) -> NoReturn:
    echo(msg, color=colors.RED)
    sys.exit(1)


def done(msg: str) -> NoReturn:
    echo(msg, color=colors.GREEN)
    sys.exit(0)

def ask(msg: str, default: bool, quiet: bool) -> bool:
    msg += ' [Y/n]' if default else ' [y/N]'
    echo(msg, colors.YELLOW)

    if quiet:
        return default
    if default:
        return input().lower() not in ('n', 'no')
    else:
        return input().lower() in ('y', 'yes')

def main(quiet: bool) -> None:
    if sys.version_info < (3, 10):
        fail('DipDup requires Python 3.10')

    echo('Welcome to DipDup installer')

    if not which('pipx'):
        echo('Installing pipx')
        run('pip install --user -q pipx')
        run('python -m pipx ensurepath')

    pipx_packages_raw = run('pipx list --short', capture_output=True).stdout
    pipx_packages = {p.split()[0].decode() for p in pipx_packages_raw.splitlines()}

    if 'dipdup' not in pipx_packages:
        echo('Installing DipDup')
        run('pipx install dipdup')
    else:
        echo('Updating DipDup')
        run('pipx upgrade dipdup')

    # NOTE: May be available system-wide
    if not which('cookiecutter'):
        if ask('Install cookiecutter? Required for `dipdup new` command', True, quiet):
            echo('Installing cookiecutter')
            run('pipx install cookiecutter')

    if not which('poetry'):
        if ask('Install poetry? Optional for `dipdup new` command', True, quiet):
            echo('Installing poetry')
            run('pipx install poetry')

    done('Done! DipDup is ready to use. Run `dipdup new` to create a new project')


if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) not in (0, 1):
        fail('Usage: install.py [-q | --quiet]')

    main('--quiet' in args or '-q' in args)
