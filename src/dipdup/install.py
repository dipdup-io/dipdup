"""This script (un)installs DipDup and its dependencies with pipx.

WARNING: No imports allowed here except stdlib! Otherwise, `curl | python` magic will break.

Some functions are importable for internal use in `dipdup.cli`.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path
from shutil import which
from typing import NoReturn
from typing import Set

GITHUB = 'https://github.com/dipdup-net/dipdup.git'


def run(*args, **kwargs):
    """Run shell command"""
    return subprocess.run(
        *args,
        **kwargs,
        check=True,
        shell=True,
    )


class colors:
    """ANSI color codes"""

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


def ensure_git() -> None:
    """Ensure git is installed"""
    if which('git'):
        return

    fail('git is required to install DipDup from ref')


def ensure_pipx() -> None:
    """Ensure pipx is installed for current user"""
    if which('pipx'):
        return

    echo('Installing pipx')
    run('pip install --user -q pipx')
    run('python -m pipx ensurepath')


def get_pipx_packages() -> Set[str]:
    """Get installed pipx packages"""
    ensure_pipx()
    pipx_packages_raw = run('pipx list --short', capture_output=True).stdout
    return {p.split()[0].decode() for p in pipx_packages_raw.splitlines()}


def install(
    quiet: bool,
    force: bool,
    ref: str | None,
    path: str | None,
) -> None:
    """Install DipDup and its dependencies with pipx"""
    if ref and path:
        fail('Specify either ref or path, not both')

    force_str = '--force' if force else ''
    pipx_packages = get_pipx_packages()
    pipx_dipdup = 'dipdup' in pipx_packages
    pipx_datamodel_codegen = 'datamodel-code-generator' in pipx_packages
    pipx_poetry = 'poetry' in pipx_packages

    if pipx_dipdup:
        echo('Updating DipDup')
        run(f'pipx upgrade dipdup {force_str}')
    else:
        if path:
            echo(f'Installing DipDup from `{path}`')
            run(f'pipx install {path} {force_str}')
        elif ref:
            echo(f'Installing DipDup from `{ref}`')
            run(f'pipx install git+{GITHUB}@{ref} {force_str}')
        else:
            echo('Installing DipDup from PyPI')
            run(f'pipx install dipdup {force_str}')

    if pipx_datamodel_codegen:
        run(f'pipx upgrade datamodel-code-generator {force_str}')
    else:
        run(f'pipx install datamodel-code-generator {force_str}')

    if (legacy_poetry := Path(Path.home(), '.poetry')).exists():
        os.rmdir(legacy_poetry)
        run(f'pipx install poetry {force_str}')
    elif pipx_poetry:
        echo('Updating Poetry')
        run(f'pipx upgrade poetry {force_str}')
    elif ask('Install poetry? Optional for `dipdup new` command', True, quiet):
        echo('Installing poetry')
        run(f'pipx install poetry {force_str}')

    done('Done! DipDup is ready to use.\nRun `dipdup new` to create a new project or `dipdup` to see all available commands.')


def uninstall(quiet: bool) -> NoReturn:
    """Uninstall DipDup and its dependencies with pipx"""
    pipx_packages = get_pipx_packages()

    if 'dipdup' in pipx_packages:
        echo('Uninstalling DipDup')
        run('pipx uninstall dipdup')

    if 'datamodel-code-generator' in pipx_packages:
        if ask('Uninstall datamodel-code-generator?', True, quiet):
            echo('Uninstalling datamodel-code-generator')
            run('pipx uninstall datamodel-code-generator')

    done('Done! DipDup is uninstalled.')


def _check_system() -> None:
    if not sys.version.startswith('3.10'):
        fail('DipDup requires Python 3.10')

    # NOTE: Show warning if user is root
    if os.geteuid() == 0:
        echo('WARNING: Running as root, this is not generally recommended', colors.YELLOW)

    # NOTE: Show warning if user is in virtualenv
    if sys.base_prefix != sys.prefix:
        echo('WARNING: Running in virtualenv, this script affects only current user', colors.YELLOW)


def cli() -> None:
    echo('Welcome to DipDup installer')

    _check_system()

    parser = argparse.ArgumentParser()
    parser.add_argument('-q', '--quiet', action='store_true', help='Use default answers for all questions')
    parser.add_argument('-f', '--force', action='store_true', help='Force reinstall')
    parser.add_argument('-r', '--ref', help='Install DipDup from a specific git ref')
    parser.add_argument('-p', '--path', help='Install DipDup from a local path')
    parser.add_argument('-u', '--uninstall', action='store_true', help='Uninstall DipDup')
    args = parser.parse_args()

    if args.uninstall:
        uninstall(args.quiet)
    else:
        install(
            quiet=args.quiet,
            force=args.force,
            ref=args.ref.strip() if args.ref else None,
            path=args.path.strip() if args.path else None,
        )


if __name__ == '__main__':
    cli()
