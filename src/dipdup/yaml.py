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
from io import StringIO
from os import environ as env
from pathlib import Path

from pydantic.json import pydantic_encoder
from ruamel.yaml import YAML

from dipdup.exceptions import ConfigurationError
from dipdup.utils import exclude_none

# NOTE: ${VARIABLE:-default} | ${VARIABLE}
ENV_VARIABLE_REGEX = r'\$\{(?P<var_name>[\w]+)(?:\:\-(?P<default_value>.*?))?\}'


_logger = logging.getLogger('dipdup.yaml')


class DipDupYAMLConfig(dict):
    @classmethod
    def load(
        cls,
        paths: list[Path],
        environment: bool = True,
    ) -> DipDupYAMLConfig:
        yaml = YAML(typ='base')

        json_config = cls()
        config_environment: dict[str, str] = {}
        for path in paths:
            raw_config = cls._load_raw_config(path)

            if environment:
                raw_config, raw_config_environment = cls._substitute_env_variables(raw_config)
                config_environment.update(raw_config_environment)

            json_config.update(yaml.load(raw_config))

        return json_config

    def dump(self) -> str:
        yaml = YAML(typ='unsafe', pure=True)
        yaml.default_flow_style = False
        yaml.indent = 2

        config_json = json.dumps(self, default=pydantic_encoder)
        config_yaml = exclude_none(yaml.load(config_json))
        buffer = StringIO()
        yaml.dump(config_yaml, buffer)
        return buffer.getvalue()

    @classmethod
    def _load_raw_config(cls, path: Path) -> str:
        _logger.debug('Loading config from %s', path)
        try:
            with open(path) as file:
                return ''.join(filter(cls._filter_commented_lines, file.readlines()))
        except OSError as e:
            raise ConfigurationError(str(e)) from e

    @classmethod
    def _filter_commented_lines(cls, line: str) -> bool:
        return '#' not in line or line.lstrip()[0] != '#'

    @classmethod
    def _substitute_env_variables(cls, raw_config: str) -> tuple[str, dict[str, str]]:
        _logger.debug('Substituting environment variables')
        environment: dict[str, str] = {}

        for match in re.finditer(ENV_VARIABLE_REGEX, raw_config):
            variable, default_value = match.group('var_name'), match.group('default_value')
            value = env.get(variable, default_value)
            if not value:
                raise ConfigurationError(f'Environment variable `{variable}` is not set')
            environment[variable] = value
            placeholder = match.group(0)
            raw_config = raw_config.replace(placeholder, value or default_value)

        return raw_config, environment
