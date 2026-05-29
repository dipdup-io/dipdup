from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from dipdup.config import HttpConfig
from dipdup.config import Url
from dipdup.config._subsquid import SubsquidDatasourceConfig


@dataclass(config=ConfigDict(extra='forbid', defer_build=True), kw_only=True)
class EvmPortalDatasourceConfig(SubsquidDatasourceConfig):
    """SQD Portal datasource config

    :param kind: always 'evm.sqd_portal'
    :param url: URL of the SQD Portal dataset
    :param api_key: API key
    :param http: HTTP client configuration
    """

    kind: Literal['evm.sqd_portal'] = 'evm.sqd_portal'
    url: Url
    api_key: str | None = None
    http: HttpConfig | None = None
