import importlib
import importlib.util
import platform
from contextlib import suppress
from os import environ as env
from pathlib import Path


def get_package_path(package: str) -> Path:
    """Absolute path to the indexer package, existing or default"""

    # NOTE: Integration tests run in isolated environment
    if TEST:
        return Path.cwd() / package

    # NOTE: If cwd is a package, use it
    if Path('pyproject.toml').exists() and Path.cwd().name == package:
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
    REPLAY_PATH = str(Path(__file__).parent.parent.parent / 'tests' / 'replays')
    env['DIPDUP_REPLAY_PATH'] = REPLAY_PATH


if get('CI') == 'true':
    env['DIPDUP_CI'] = '1'
if platform.system() == 'Linux' and Path('/.dockerenv').exists():
    env['DIPDUP_DOCKER'] = '1'

CI = get_bool('DIPDUP_CI')
DOCKER = get_bool('DIPDUP_DOCKER')
NEXT = get_bool('DIPDUP_NEXT')
REPLAY_PATH = get_path('DIPDUP_REPLAY_PATH')
TEST = get_bool('DIPDUP_TEST')
