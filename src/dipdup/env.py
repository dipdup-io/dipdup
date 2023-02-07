import importlib
import platform
from contextlib import suppress
from os import environ as env
from pathlib import Path
from typing import cast


def get_package_path(package: str) -> Path:
    """Absolute path to the indexer package, existing or default"""
    global PACKAGE_PATH

    # NOTE: Integration tests run in isolated environment
    if TEST:
        set_package_path(Path.cwd() / package)

    if PACKAGE_PATH:
        return PACKAGE_PATH

    # NOTE: Detect existing package in current environment
    with suppress(ImportError):
        module = importlib.import_module(package)
        if module.__file__ is None:
            raise RuntimeError(f'`{module.__name__}` package has no `__file__` attribute')
        set_package_path(Path(module.__file__).parent)
        return cast(Path, PACKAGE_PATH)

    # NOTE: Create a new package; try src/<package> layout first.
    if Path('src').is_dir():
        set_package_path(Path('src', package))
    else:
        set_package_path(Path(package))

    return cast(Path, PACKAGE_PATH)


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
    REPLAY_PATH = str(Path(__file__).parent.parent.parent.parent / 'tests' / 'replays')
    env['DIPDUP_REPLAY_PATH'] = REPLAY_PATH


def set_package_path(path: Path) -> None:
    global PACKAGE_PATH
    PACKAGE_PATH = path
    env['DIPDUP_PACKAGE_PATH'] = str(path)


if get('CI') == 'true':
    env['DIPDUP_CI'] = '1'
if platform.system() == 'Linux' and Path('/.dockerenv').exists():
    env['DIPDUP_DOCKER'] = '1'

TEST = get_bool('DIPDUP_TEST')
CI = get_bool('DIPDUP_CI')
DOCKER = get_bool('DIPDUP_DOCKER')
NEXT = get_bool('DIPDUP_NEXT')
DOCKER_IMAGE = get('DIPDUP_DOCKER_IMAGE')
PACKAGE_PATH = get_path('DIPDUP_PACKAGE_PATH')
REPLAY_PATH = get_path('DIPDUP_REPLAY_PATH')
