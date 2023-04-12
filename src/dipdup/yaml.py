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

import json
import logging.config
import re
from copy import copy
from io import StringIO
from os import environ as env
from pathlib import Path
from typing import Any

from pydantic.json import pydantic_encoder
from ruamel.yaml import YAML

from dipdup import __spec_version__
from dipdup.exceptions import ConfigurationError

# NOTE: ${VARIABLE:-default} | ${VARIABLE}
ENV_VARIABLE_REGEX = r'\$\{(?P<var_name>[\w]+)(?:\:\-(?P<default_value>.*?))?\}'


_logger = logging.getLogger('dipdup.yaml')


def exclude_none(config_json: Any) -> Any:
    if isinstance(config_json, (list, tuple)):
        return [exclude_none(i) for i in config_json if i is not None]
    if isinstance(config_json, dict):
        return {k: exclude_none(v) for k, v in config_json.items() if v is not None}
    return config_json


def filter_comments(line: str) -> bool:
    return '#' not in line or line.lstrip()[0] != '#'


def read_config_yaml(path: Path) -> str:
    _logger.debug('Loading config from %s', path)
    try:
        with open(path) as file:
            return ''.join(filter(filter_comments, file.readlines()))
    except OSError as e:
        raise ConfigurationError(f'Config file `{path}` is missing or not readable.') from e


def substitute_env_variables(config_yaml: str) -> tuple[str, dict[str, str]]:
    _logger.debug('Substituting environment variables')
    environment: dict[str, str] = {}

    for match in re.finditer(ENV_VARIABLE_REGEX, config_yaml):
        variable, default_value = match.group('var_name'), match.group('default_value')
        value = env.get(variable, default_value)
        # NOTE: Don't fail on ''
        if value is None:
            raise ConfigurationError(f'Environment variable `{variable}` is not set')
        environment[variable] = value
        placeholder = match.group(0)
        config_yaml = config_yaml.replace(placeholder, value or default_value)

    return config_yaml, environment


def fix_dataclass_field_aliases(config: dict[str, Any]) -> None:
    for k, v in copy(config).items():
        if 'callack' in config and k == 'from':
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
    ) -> tuple[DipDupYAMLConfig, dict[str, Any]]:
        yaml = YAML(typ='base')

        config = cls()
        config_environment: dict[str, str] = {}

        for path in paths:
            path_yaml = read_config_yaml(path)

            if environment:
                path_yaml, path_environment = substitute_env_variables(path_yaml)
                config_environment.update(path_environment)

            config.update(yaml.load(path_yaml))

        config.validate_version()

        # FIXME: Can't use `from_` field alias in dataclass; fixed in dipdup.yaml instead
        # FIXME: See https://github.com/pydantic/pydantic/issues/4286
        fix_dataclass_field_aliases(config)

        return config, config_environment

    def dump(self) -> str:
        yaml = YAML(typ='unsafe', pure=True)
        yaml.default_flow_style = False
        yaml.indent = 2

        config_json = json.dumps(self, default=pydantic_encoder)
        config_yaml = exclude_none(yaml.load(config_json))
        buffer = StringIO()
        yaml.dump(config_yaml, buffer)
        return buffer.getvalue()

    def validate_version(self) -> None:
        config_spec_version = self['spec_version']
        if config_spec_version != __spec_version__:
            raise ConfigurationError(
                f'Incompatible spec version: expected {__spec_version__}, got {config_spec_version}. See https://docs.dipdup.io/config/spec_version'
            )
