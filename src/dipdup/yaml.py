"""This module contains YAML-related utilities used in `dipdup.config` module.

`ruamel.yaml` and `pydantic` don't play well together, so we have to deserialize YAML into
dataclasses first with loose validation, then convert them into more strict `BaseModel`-based
classes.

Tasks performed at the first stage:

- Environment variables substitution (e.g. `${FOO}` -> `bar`)
- Merging config from multiple files (currently, only first level deep)
- Resolving aliases and references to remove `str` from union types
"""

from __future__ import annotations

import logging.config
import re
from copy import copy
from io import StringIO
from os import environ as env
from typing import TYPE_CHECKING
from typing import Any

from ruamel.yaml import YAML

from dipdup.exceptions import ConfigurationError

if TYPE_CHECKING:
    from pathlib import Path

# NOTE: ${VARIABLE:-default} | ${VARIABLE}
ENV_VARIABLE_REGEX = r'\$\{(?P<var_name>[\w]+)(?:\:\-(?P<default_value>.*?))?\}'


_logger = logging.getLogger(__name__)

yaml_loader = YAML()

yaml_dumper = YAML()
yaml_dumper.default_flow_style = False
yaml_dumper.indent(mapping=2, sequence=4, offset=2)


def filter_config_json(config_json: Any, strip_secrets: bool = False) -> Any:
    """Exclude `None` values, private fields and secrets from config JSON."""
    secrets = {'password', 'api_key', 'secret'}
    if isinstance(config_json, list | tuple):
        return [
            filter_config_json(i, strip_secrets)
            for i in config_json
            if i is not None and not (strip_secrets and isinstance(i, str) and any(s in i for s in secrets))
        ]
    if isinstance(config_json, dict):
        return {
            k: filter_config_json(v, strip_secrets)
            for k, v in config_json.items()
            if v is not None and not k.startswith('_') and not (strip_secrets and any(s in k for s in secrets))
        }
    return config_json


def filter_comments(line: str) -> bool:
    return '#' not in line or line.lstrip()[0] != '#'


def read_config_yaml(path: Path) -> str:
    _logger.debug('Discovering config `%s`', path)
    if path.is_dir():
        path /= 'dipdup.yaml'

    yml_path = path.with_suffix('.yml')
    yaml_path = path.with_suffix('.yaml')
    if path.is_file():
        pass
    elif yml_path.is_file():
        path = yml_path
    elif yaml_path.is_file():
        path = yaml_path
    else:
        raise ConfigurationError(f'Config file `{path}` is missing.')

    _logger.debug('Loading config file `%s`', path)
    try:
        with path.open() as file:
            return ''.join(filter(filter_comments, file.readlines()))
    except OSError as e:
        raise ConfigurationError(f'Config file `{path}` is not readable: {e}') from e


def dump(value: dict[str, Any], strip_secrets: bool = False) -> str:
    value = filter_config_json(value, strip_secrets)
    buffer = StringIO()
    yaml_dumper.dump(value, buffer)
    return buffer.getvalue()


def substitute_env_variables(
    config_yaml: str,
    unsafe: bool,
) -> tuple[str, dict[str, str]]:
    _logger.debug('Substituting environment variables')
    environment: dict[str, str] = {}

    for match in re.finditer(ENV_VARIABLE_REGEX, config_yaml):
        variable, default_value = match.group('var_name'), match.group('default_value')

        if unsafe:
            value = env.get(variable, default_value)
            # NOTE: Don't fail on ''
            if value is None:
                raise ConfigurationError(f'Environment variable `{variable}` is not set')
        else:
            value = default_value or ''

        environment[variable] = value
        placeholder = match.group(0)
        config_yaml = config_yaml.replace(placeholder, value)

    return config_yaml, environment


def get_default_env_variables(config_yaml: str) -> dict[str, str]:
    environment: dict[str, str] = {}

    for match in re.finditer(ENV_VARIABLE_REGEX, config_yaml):
        variable, default_value = match.group('var_name'), match.group('default_value')
        environment[variable] = default_value or ''

    return environment


# FIXME: Can't use `from_` field alias in dataclasses
def fix_dataclass_field_aliases(config: dict[str, Any]) -> None:
    for k, v in copy(config).items():
        if 'callback' in config and k == 'from':
            config['from_'] = config.pop('from')
        elif isinstance(v, dict):
            fix_dataclass_field_aliases(v)
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    fix_dataclass_field_aliases(item)


class DipDupYAMLConfig(dict[str, Any]):
    @classmethod
    def load(
        cls,
        paths: list[Path],
        environment: bool = True,
        raw: bool = False,
        unsafe: bool = False,
    ) -> tuple[DipDupYAMLConfig, dict[str, Any]]:
        config = cls()
        config_environment: dict[str, str] = {}

        for path in paths:
            path_yaml = read_config_yaml(path)

            if raw:
                pass
            elif environment:
                path_yaml, path_environment = substitute_env_variables(path_yaml, unsafe)
                config_environment.update(path_environment)

            config.update(yaml_loader.load(path_yaml))

        if not raw:
            # FIXME: Can't use `from_` field alias in dataclasses
            fix_dataclass_field_aliases(config)

        return config, config_environment

    def dump(self, strip_secrets: bool = False) -> str:
        return dump(self, strip_secrets)
