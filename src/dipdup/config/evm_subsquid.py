from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from dipdup.config import HttpConfig
from dipdup.config import IndexDatasourceConfig
from dipdup.config import Url


@dataclass(config=ConfigDict(extra='forbid'), kw_only=True)
class EvmSubsquidDatasourceConfig(IndexDatasourceConfig):
    """Subsquid datasource config

    :param kind: always 'evm.subsquid'
    :param url: URL of Subsquid Network API
    :param http: HTTP client configuration
    """

    kind: Literal['evm.subsquid']
    url: Url
    http: HttpConfig | None = None

    @property
    def merge_subscriptions(self) -> bool:
        return False

    @property
    def rollback_depth(self) -> int:
        return 0
