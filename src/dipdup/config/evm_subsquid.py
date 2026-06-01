from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from dipdup.config import HttpConfig
from dipdup.config import Url
from dipdup.config._subsquid import SubsquidDatasourceConfig


@dataclass(config=ConfigDict(extra='forbid', defer_build=True), kw_only=True)
class EvmSubsquidDatasourceConfig(SubsquidDatasourceConfig):
    """Subsquid datasource config

    :param kind: always 'evm.subsquid'
    :param url: URL of Subsquid Network API
    :param api_key: API key
    :param http: HTTP client configuration
    """

    kind: Literal['evm.subsquid'] = 'evm.subsquid'
    url: Url
    http: HttpConfig | None = None
