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

import hashlib
import importlib
import json
import logging.config
import re
from abc import ABC
from abc import abstractmethod
from collections import Counter
from collections import defaultdict
from contextlib import suppress
from copy import copy
from dataclasses import field
from functools import cached_property
from io import StringIO
from os import environ as env
from pathlib import Path
from pydoc import locate
from typing import Any
from typing import Awaitable
from typing import Callable
from typing import Generic
from typing import Iterator
from typing import Sequence
from typing import TypeVar
from typing import cast
from urllib.parse import quote_plus
from urllib.parse import urlparse

from pydantic import Field
from pydantic import validator
from pydantic.dataclasses import dataclass
from pydantic.json import pydantic_encoder
from ruamel.yaml import YAML
from typing_extensions import Literal

from dipdup import baking_bad
from dipdup.datasources.metadata.enums import MetadataNetwork
from dipdup.datasources.subscription import Subscription
from dipdup.datasources.tzkt.models import BigMapSubscription
from dipdup.datasources.tzkt.models import EventSubscription
from dipdup.datasources.tzkt.models import HeadSubscription
from dipdup.datasources.tzkt.models import OriginationSubscription
from dipdup.datasources.tzkt.models import TokenTransferSubscription
from dipdup.datasources.tzkt.models import TransactionSubscription
from dipdup.enums import LoggingValues
from dipdup.enums import OperationType
from dipdup.enums import ReindexingAction
from dipdup.enums import ReindexingReason
from dipdup.enums import SkipHistory
from dipdup.exceptions import ConfigInitializationException
from dipdup.exceptions import ConfigurationError
from dipdup.exceptions import IndexAlreadyExistsError
from dipdup.utils import exclude_none
from dipdup.utils import import_from
from dipdup.utils import pascal_to_snake
from dipdup.utils import snake_to_pascal
from dipdup.utils.sys import is_in_tests

# NOTE: ${VARIABLE:-default} | ${VARIABLE}
ENV_VARIABLE_REGEX = r'\$\{(?P<var_name>[\w]+)(?:\:\-(?P<default_value>.*?))?\}'


_logger = logging.getLogger('dipdup.yaml')


@dataclass
class DipDupYAMLConfig:
    spec_version: str
    package: str
    datasources: dict[str, dict[str, Any]] = field(default_factory=dict)
    database: dict[str, Any] = field(default_factory=dict)
    contracts: dict[str, dict[str, Any]] = field(default_factory=dict)
    indexes: dict[str, dict[str, Any]] = field(default_factory=dict)
    templates: dict[str, dict[str, Any]] = field(default_factory=dict)
    hooks: dict[str, dict[str, Any]] = field(default_factory=dict)
    jobs: dict[str, Any] = field(default_factory=dict)
    hasura: dict[str, Any] | None = None
    sentry: dict[str, Any] | None = None
    prometheus: dict[str, Any] | None = None
    advanced: dict[str, Any] = field(default_factory=dict)
    custom: dict[str, Any] = field(default_factory=dict)
    logging: str | None = None

    def __post_init_post_parse__(self) -> None:
        if self.package != pascal_to_snake(self.package):
            # TODO: Remove in 7.0
            # raise ConfigurationError('Python package name must be in snake_case.')
            _logger.warning('Python package name must be in snake_case.')

        self.paths: list[Path] = []
        self.environment: dict[str, str] = {}

    @classmethod
    def load(
        cls,
        paths: list[Path],
        environment: bool = True,
    ) -> DipDupYAMLConfig:
        yaml = YAML(typ='base')

        json_config: dict[str, Any] = {}
        config_environment: dict[str, str] = {}
        for path in paths:
            raw_config = cls._load_raw_config(path)

            if environment:
                raw_config, raw_config_environment = cls._substitute_env_variables(raw_config)
                config_environment.update(raw_config_environment)

            json_config.update(yaml.load(raw_config))

        try:
            config = cls(**json_config)
        except ConfigurationError:
            raise
        except Exception as e:
            raise ConfigurationError(str(e)) from e

        config.environment = config_environment
        config.paths = paths
        return config

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
