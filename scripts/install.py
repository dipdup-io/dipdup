import os
import subprocess
import sys
from shutil import which
from typing import NoReturn


def run(*args, **kwargs):
    return subprocess.run(
        *args,
        **kwargs,
        check=True,
        shell=True,
    )


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


def main(quiet: bool, local: bool) -> None:
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
        if local:
            echo(f'Installing DipDup from `{os.getcwd()}`')
            run('pipx install .')
        else:
            echo(f'Installing DipDup from PyPI')
            run('pipx install dipdup')
    else:
        echo('Updating DipDup')
        run('pipx upgrade dipdup')

    if 'datamodel-code-generator' not in pipx_packages:
        run('pipx install datamodel-code-generator')
    else:
        run('pipx upgrade datamodel-code-generator')

    if not which('poetry'):
        if ask('Install poetry? Optional for `dipdup new` command', True, quiet):
            echo('Installing poetry')
            run('pipx install poetry')

    done('Done! DipDup is ready to use.\nRun `dipdup new` to create a new project or `dipdup` to see all available commands.')


if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) not in (0, 1, 2):
        fail('usage: install.py [-q | --quiet] | [-l | --local]')

    quiet = '--quiet' in args or '-q' in args
    local = '--local' in args or '-l' in args
    main(quiet, local)
