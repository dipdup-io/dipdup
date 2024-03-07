import importlib
import importlib.util
import platform
import tomllib
from contextlib import suppress
from os import environ as env
from pathlib import Path

from dipdup.exceptions import FrameworkException


def get_pyproject_name() -> str | None:
    pyproject_path = Path('pyproject.toml')
    if not pyproject_path.exists():
        return None

    content = tomllib.loads(pyproject_path.read_text())
    if 'project' in content:
        return str(content['project']['name'])
    if 'tool' in content and 'poetry' in content['tool']:
        return str(content['tool']['poetry']['name'])
    raise FrameworkException('`pyproject.toml` found, but has neither `project` nor `tool.poetry` section')


def get_package_path(package: str) -> Path:
    """Absolute path to the indexer package, existing or default"""

    # NOTE: Integration tests run in isolated environment
    if TEST:
        return Path.cwd() / package

    # NOTE: If cwd is a package, use it
    if get_pyproject_name() == package:
        return Path.cwd()

    # NOTE: Detect existing package in current environment
    with suppress(ImportError):
        module = importlib.import_module(package)
        if module.__file__ is None:
            raise ImportError(f'`{module.__name__}` package has no `__file__` attribute')
        return Path(module.__file__).parent

    # NOTE: Create a new package
    return Path.cwd() / package


def get(key: str, default: str | None = None) -> str | None:
    return env.get(key, default)


def get_bool(key: str) -> bool:
    return (get(key) or '').lower() in ('1', 'y', 'yes', 't', 'true', 'on')


def get_int(key: str, default: int) -> int:
    return int(get(key) or default)


def get_path(key: str) -> Path | None:
    value = get(key)
    if value is None:
        return None
    return Path(value)


def set_test() -> None:
    global TEST, REPLAY_PATH
    TEST = True
    REPLAY_PATH = Path(__file__).parent.parent.parent / 'tests' / 'replays'


CI: bool
DEBUG: bool
DOCKER: bool
NEXT: bool
NO_SYMLINK: bool
NO_VERSION_CHECK: bool
REPLAY_PATH: Path | None
TEST: bool


def dump() -> dict[str, str]:
    return {
        'DIPDUP_CI': get('DIPDUP_CI') or '',
        'DIPDUP_DEBUG': get('DIPDUP_DEBUG') or '',
        'DIPDUP_DOCKER': get('DIPDUP_DOCKER') or '',
        'DIPDUP_NEXT': get('DIPDUP_NEXT') or '',
        'DIPDUP_NO_SYMLINK': get('DIPDUP_NO_SYMLINK') or '',
        'DIPDUP_NO_VERSION_CHECK': get('DIPDUP_NO_VERSION_CHECK') or '',
        'DIPDUP_REPLAY_PATH': get('DIPDUP_REPLAY_PATH') or '',
        'DIPDUP_TEST': get('DIPDUP_TEST') or '',
    }


def read() -> None:
    global CI, DEBUG, DOCKER, NEXT, NO_SYMLINK, NO_VERSION_CHECK, REPLAY_PATH, TEST
    CI = get_bool('DIPDUP_CI')
    DEBUG = get_bool('DIPDUP_DEBUG')
    DOCKER = get_bool('DIPDUP_DOCKER')
    NEXT = get_bool('DIPDUP_NEXT')
    NO_SYMLINK = get_bool('DIPDUP_NO_SYMLINK')
    NO_VERSION_CHECK = get_bool('DIPDUP_NO_VERSION_CHECK')
    REPLAY_PATH = get_path('DIPDUP_REPLAY_PATH')
    TEST = get_bool('DIPDUP_TEST')

    if get('CI') == 'true':
        CI = True
    if platform.system() == 'Linux' and Path('/.dockerenv').exists():
        DOCKER = True


read()
