import importlib
import importlib.util
import platform
import sys
import tomllib
from contextlib import suppress
from pathlib import Path

from pydantic import AliasChoices
from pydantic import AliasGenerator
from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

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

    if ENV_MODEL.PACKAGE_PATH:
        spec = importlib.util.spec_from_file_location(package, ENV_MODEL.PACKAGE_PATH / '__init__.py')
        if spec is None:
            raise ImportError(f'Failed to import `{package}` package from `{ENV_MODEL.PACKAGE_PATH}`')
        module = importlib.util.module_from_spec(spec)
        sys.modules[package] = module
        if spec.loader is None:
            raise ImportError(f'Failed to import `{package}` package from `{ENV_MODEL.PACKAGE_PATH}`')
        spec.loader.exec_module(module)
        return ENV_MODEL.PACKAGE_PATH

    # NOTE: Integration tests run in isolated environment
    if ENV_MODEL.TEST:
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


def set_test() -> None:
    ENV_MODEL.TEST = True
    ENV_MODEL.REPLAY_PATH = Path(__file__).parent.parent.parent / 'tests' / 'replays'


class DipDupSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix='DIPDUP_',
        extra='allow',
        case_sensitive=True,
        env_ignore_empty=True,
        alias_generator=AliasGenerator(serialization_alias=lambda s: f'DIPDUP_{s}'),
    )

    CI: bool = Field(default=False, validation_alias=AliasChoices('DIPDUP_CI', 'CI'))
    DEBUG: bool = False
    DOCKER: bool = Field(default_factory=lambda: platform.system() == 'Linux' and Path('/.dockerenv').exists())
    JSON_LOG: bool = False
    LOW_MEMORY: bool = False
    NEXT: bool = False
    NO_SYMLINK: bool = False
    NO_VERSION_CHECK: bool = False
    PACKAGE_PATH: Path | None = None
    REPLAY_PATH: Path | None = None
    TEST: bool = False


ENV_MODEL = DipDupSettings()
