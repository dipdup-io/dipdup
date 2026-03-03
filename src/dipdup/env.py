import importlib
import importlib.util
import platform
import sys
import tomllib
from contextlib import suppress
from functools import cache
from os import getenv
from pathlib import Path

from dipdup.exceptions import FrameworkException


def dump() -> dict[str, str]:
    result: dict[str, str] = {}
    for key in globals().keys():
        if key.isupper():
            result[f'DIPDUP_{key}'] = getenv(f'DIPDUP_{key}') or ''
    return result


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


@cache
def get_package_path(package: str) -> Path:
    """Absolute path to the indexer package, existing or default"""

    if PACKAGE_PATH:
        spec = importlib.util.spec_from_file_location(package, PACKAGE_PATH / '__init__.py')
        if spec is None:
            raise ImportError(f'Failed to import `{package}` package from `{PACKAGE_PATH}`')
        module = importlib.util.module_from_spec(spec)
        sys.modules[package] = module
        if spec.loader is None:
            raise ImportError(f'Failed to import `{package}` package from `{PACKAGE_PATH}`')
        spec.loader.exec_module(module)
        return PACKAGE_PATH

    # NOTE: Integration tests run in isolated environment
    if TEST:
        return Path.cwd() / package

    # NOTE: If cwd is a package, use it
    if package in {get_pyproject_name(), Path.cwd().name}:
        return Path.cwd()

    # NOTE: Detect existing package in current environment
    with suppress(ImportError):
        module = importlib.import_module(package)
        if module.__file__:
            return Path(module.__file__).parent
        if module.__path__:
            return Path(module.__path__[0])

    # NOTE: Create a new package
    return Path.cwd() / package


def get_bool(key: str) -> bool:
    return (getenv(key) or '').lower() in ('1', 'y', 'yes', 't', 'true', 'on')


def get_int(key: str, default: int) -> int:
    return int(getenv(key) or default)


def get_path(key: str) -> Path | None:
    value = getenv(key)
    if value is None:
        return None
    return Path(value)


def reload_env() -> None:
    global \
        DEBUG, \
        JSON_LOG, \
        LOW_MEMORY, \
        MIGRATIONS, \
        NEXT, \
        NO_LINTER, \
        NO_BASE, \
        NO_HOOKS, \
        NO_SYMLINK, \
        PACKAGE_PATH, \
        REPLAY_PATH, \
        TEST

    DEBUG = get_bool('DIPDUP_DEBUG')
    JSON_LOG = get_bool('DIPDUP_JSON_LOG')
    LOW_MEMORY = get_bool('DIPDUP_LOW_MEMORY')
    MIGRATIONS = get_bool('DIPDUP_MIGRATIONS')
    NEXT = get_bool('DIPDUP_NEXT')
    NO_LINTER = get_bool('DIPDUP_NO_LINTER')
    NO_BASE = get_bool('DIPDUP_NO_BASE')
    NO_HOOKS = get_bool('DIPDUP_NO_HOOKS')
    NO_SYMLINK = get_bool('DIPDUP_NO_SYMLINK')
    PACKAGE_PATH = get_path('DIPDUP_PACKAGE_PATH')
    REPLAY_PATH = get_path('DIPDUP_REPLAY_PATH')
    TEST = get_bool('DIPDUP_TEST')


def set_test() -> None:
    global TEST, REPLAY_PATH
    TEST = True
    REPLAY_PATH = Path(__file__).parent.parent.parent / 'tests' / 'replays'


def extract_docstrings() -> dict[str, str]:
    import inspect
    import re

    source = inspect.getsource(sys.modules[__name__])
    pattern = r'([A-Za-z_][A-Za-z0-9_]*)\s*(?::\s*[^=\n]+)?\s*=\s*[^\n]+\n\s*"""([^"]*)"""'
    matches = re.findall(pattern, source)
    return {f'DIPDUP_{k}': v.strip() for k, v in matches}


DEBUG: bool = get_bool('DIPDUP_DEBUG')
"""Enable debug logging and additional checks"""

JSON_LOG: bool = get_bool('DIPDUP_JSON_LOG')
"""Print logs in JSON format"""

LOW_MEMORY: bool = get_bool('DIPDUP_LOW_MEMORY')
"""Reduce the size of caches and buffers for low-memory environments (only for debugging!)"""

MIGRATIONS: bool = get_bool('DIPDUP_MIGRATIONS')
"""Enable migrations with `aerich`"""

NEXT: bool = get_bool('DIPDUP_NEXT')
"""Enable experimental and breaking features from the next major release"""

NO_LINTER: bool = get_bool('DIPDUP_NO_LINTER')
"""Don't format and lint generated files with ruff"""

NO_BASE: bool = get_bool('DIPDUP_NO_BASE')
"""Don't recreate files from base project template"""

NO_HOOKS: bool = get_bool('DIPDUP_NO_HOOKS')
"""Don't run hooks, both internal and user-defined"""

NO_SYMLINK: bool = get_bool('DIPDUP_NO_SYMLINK')
"""Don't create magic symlink in the package root even when used as cwd"""

PACKAGE_PATH: Path | None = get_path('DIPDUP_PACKAGE_PATH')
"""Disable package discovery and use the specified path"""

REPLAY_PATH: Path | None = get_path('DIPDUP_REPLAY_PATH')
"""Path to datasource replay files; used in tests (dev only)"""

TEST: bool = get_bool('DIPDUP_TEST')
"""Running in tests (disables Sentry and some checks)"""


def is_in_gha() -> bool:
    """Check if running in GitHub Actions environment"""
    return getenv('CI') == 'true'


def is_in_docker() -> bool:
    """Check if running in Docker environment"""
    return getenv('DOCKER') == 'true' and platform.system() == 'Linux'


# TODO: Compatibility aliases, remove in 9.0
CI = is_in_gha()
DOCKER = is_in_docker()
