"""This script (un)installs DipDup and its dependencies with uv.

WARNING: No imports allowed here except stdlib! Otherwise, `curl | python` magic will break.
And no 3.12-only code too. Just to print nice colored "not supported" message instead of crashing.

Some functions are importable to use in `dipdup.cli`.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from shutil import which
from typing import Any
from typing import NoReturn

GITHUB = 'https://github.com/dipdup-io/dipdup.git'
ENV_VARS = (
    'SHELL',
    'VIRTUAL_ENV',
    'PATH',
    'PYTHONPATH',
)

# NOTE: '\0' is to avoid truncating newlines by asyncclick
WELCOME_ASCII = (
    '\0'
    + r"""
        ____   _         ____              
       / __ \ (_)____   / __ \ __  __ ____ 
      / / / // // __ \ / / / // / / // __ \
     / /_/ // // /_/ // /_/ // /_/ // /_/ /
    /_____//_// .___//_____/ \__,_// .___/ 
             /_/                  /_/      
"""
)
EPILOG = (
    '\0'
    + """
Documentation:         https://dipdup.io/docs
GitHub:                https://github.com/dipdup-io/dipdup
Discord:               https://discord.gg/aG8XKuwsQd
"""
)


class Colors:
    """ANSI color codes"""

    BLUE = '\033[34m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'


def echo(msg: str, color: str = Colors.BLUE) -> None:
    print(color + f'=> {msg}' + Colors.ENDC)


def fail(msg: str) -> NoReturn:
    echo(msg, color=Colors.RED)
    sys.exit(1)


def done(msg: str) -> NoReturn:
    echo(msg, color=Colors.GREEN)
    sys.exit(0)


# NOTE: DipDup has `tabulate` dep, don't use this one elsewhere
# NOTE: Weird default is to match indentation in `EPILOG`.
def _tab(text: str, indent: int = 23) -> str:
    return text + ' ' * (indent - len(text))


def print_greeting() -> None:
    print()
    print(Colors.GREEN + WELCOME_ASCII + Colors.ENDC)
    print(EPILOG)
    print()

    print(_tab('OS:') + f'{os.uname().sysname} ({os.uname().machine})')
    print(_tab('Python:') + sys.version)
    print()

    for var in ENV_VARS:
        if var in os.environ:
            print(_tab(var + ':') + os.environ[var])
    print()


def prepare() -> None:
    # NOTE: Show warning if user is root
    if os.geteuid() == 0:
        echo('WARNING: Running as root, this is not generally recommended', Colors.YELLOW)

    # NOTE: Show warning if user is in virtualenv
    if sys.base_prefix != sys.prefix:
        echo('WARNING: Running in virtualenv, it will be ignored', Colors.YELLOW)

    ensure_uv()


def ensure_uv() -> None:
    if not sys.version.startswith('3.12'):
        echo('WARNING: DipDup requires Python 3.12, another Python version will be installed', Colors.YELLOW)

    """Ensure uv is installed for current user"""
    if which('uv'):
        return

    echo('Installing uv')
    install_uv()
    print('_' * 80)


def install_uv() -> None:
    run_cmd('curl -LsSf https://astral.sh/uv/install.sh | sh', shell=True)
    os.environ['PATH'] = str(Path.home() / '.local' / 'bin') + os.pathsep + os.environ['PATH']


def uninstall(quiet: bool) -> NoReturn:
    """Uninstall DipDup and its dependencies with uvx"""

    package = 'dipdup'
    echo(f'Uninstalling {package}')
    run_cmd('uv', 'tool', 'uninstall', package)

    done('Done! DipDup is uninstalled.')


def install(
    quiet: bool,
    force: bool,
    version: str | None,
    ref: str | None,
    path: str | None,
    pre: bool = False,
    editable: bool = False,
    update: bool = False,
) -> None:
    """Install DipDup and its dependencies with uv"""
    if ref and path:
        fail('Specify either ref or path, not both')

    prepare()
    if not quiet:
        print_greeting()

    uv_tool_args = []
    if force:
        uv_tool_args.append('--force')
    if pre:
        uv_tool_args.append('--prerelease')
        uv_tool_args.append('allow')
    if editable:
        uv_tool_args.append('-e')

    dipdup_path = which(
        'dipdup',
        path=os.environ['PATH'].replace('.venv', 'NULL'),
    )

    if dipdup_path is not None:
        if version:
            run_cmd('uv', 'tool', 'install', f'dipdup=={version}', *uv_tool_args)
        elif update:
            run_cmd('uv', 'tool', 'upgrade', 'dipdup', *uv_tool_args)
    elif path:
        echo(f'Installing DipDup from `{path}`')
        run_cmd('uv', 'tool', 'install', path, *uv_tool_args)
    elif ref:
        url = f'git+{GITHUB}@{ref}'
        echo(f'Installing DipDup from `{url}`')
        run_cmd('uv', 'tool', 'install', url, *uv_tool_args)
    else:
        echo('Installing DipDup from PyPI')
        pkg = 'dipdup' if not version else f'dipdup=={version}'
        run_cmd('uv', 'tool', 'install', pkg, *uv_tool_args)

    done('Done! DipDup is ready to use. Run `dipdup` see available commands.')


def run_cmd(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
    print(Colors.YELLOW, f'$ {" ".join(args)}', Colors.ENDC)
    try:
        return subprocess.run(
            args,
            **kwargs,
            check=True,  # shell=true for script
        )
    except subprocess.CalledProcessError as e:
        fail(f'{args[0]} failed: {e.cmd} {e.returncode}')


def cli() -> None:
    echo('Welcome to DipDup installer')

    parser = argparse.ArgumentParser()
    parser.add_argument('-q', '--quiet', action='store_true', help='Less verbose output')
    parser.add_argument('-f', '--force', action='store_true', help='Force reinstall DipDup')
    parser.add_argument('-v', '--version', help='Install DipDup from a specific version')
    parser.add_argument('-r', '--ref', help='Install DipDup from a specific git ref')
    parser.add_argument('-p', '--path', help='Install DipDup from a local path')
    parser.add_argument('-u', '--uninstall', action='store_true', help='Uninstall DipDup')
    parser.add_argument('-U', '--update', action='store_true', help='Update DipDup')
    parser.add_argument('--pre', action='store_true', help='Include pre-release versions')
    parser.add_argument('-e', '--editable', action='store_true', help='Install DipDup in editable mode')
    args = parser.parse_args()

    if not args.quiet:
        sys.stdin = open('/dev/tty')  # noqa: PTH123

    if args.uninstall:
        uninstall(args.quiet)
    else:
        # TODO: ensure resulted version match requested version (ensure uvx tool downgrades correctly) (old force reinstall flag)
        install(
            quiet=args.quiet,
            force=args.force,
            version=args.version.strip() if args.version else None,
            ref=args.ref.strip() if args.ref else None,
            path=args.path.strip() if args.path else None,
            pre=args.pre,
            editable=args.editable,
            update=args.update,
        )


if __name__ == '__main__':
    cli()
