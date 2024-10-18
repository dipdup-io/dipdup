from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from dipdup.config import HttpConfig
from dipdup.config import IndexDatasourceConfig
from dipdup.config import Url
from dipdup.config import WsUrl


@dataclass(config=ConfigDict(extra='forbid'), kw_only=True)
class SubstrateNodeDatasourceConfig(IndexDatasourceConfig):
    """Substrate node datasource config

    :param kind: Always 'substrate.node'
    :param url: Substrate node URL
    :param ws_url: Substrate node WebSocket URL
    :param http: HTTP client configuration
    """

    kind: Literal['substrate.node']
    url: Url
    ws_url: WsUrl | None = None
    http: HttpConfig | None = None

    @property
    def merge_subscriptions(self) -> bool:
        return False

    @property
    def rollback_depth(self) -> int:
        # FIXME:
        return 0
