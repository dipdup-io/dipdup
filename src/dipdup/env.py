import importlib
import importlib.util
import platform
import tomllib
from contextlib import suppress
from os import environ as env
from pathlib import Path

from dipdup.exceptions import FrameworkException


def get_package_path(package: str) -> Path:
    """Absolute path to the indexer package, existing or default"""

    # NOTE: Integration tests run in isolated environment
    if TEST:
        return Path.cwd() / package

    # NOTE: If cwd is a package, use it
    pyproject_path = Path('pyproject.toml')
    if pyproject_path.exists():
        content = tomllib.loads(pyproject_path.read_text())
        if 'project' in content:
            pyproject_package = content['project']['name']
        elif 'tool' in content and 'poetry' in content['tool']:
            pyproject_package = content['tool']['poetry']['name']
        else:
            raise FrameworkException('`pyproject.toml` found, but has neither `project` nor `tool.poetry` section')
        if pyproject_package == package:
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


def get_bool(key: str, default: bool = False) -> bool:
    return get(key) in ('1', 'true', 'True')


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
REPLAY_PATH: Path | None
TEST: bool


def read() -> None:
    global CI, DEBUG, DOCKER, NEXT, REPLAY_PATH, TEST
    CI = get_bool('DIPDUP_CI')
    DEBUG = get_bool('DIPDUP_DEBUG')
    DOCKER = get_bool('DIPDUP_DOCKER')
    NEXT = get_bool('DIPDUP_NEXT')
    REPLAY_PATH = get_path('DIPDUP_REPLAY_PATH')
    TEST = get_bool('DIPDUP_TEST')

    if get('CI') == 'true':
        CI = True
    if platform.system() == 'Linux' and Path('/.dockerenv').exists():
        DOCKER = True


read()
