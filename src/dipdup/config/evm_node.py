from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from dipdup.config import HttpConfig
from dipdup.config import IndexDatasourceConfig
from dipdup.config import Url
from dipdup.config import WsUrl


@dataclass(config=ConfigDict(extra='forbid'), kw_only=True)
class EvmNodeDatasourceConfig(IndexDatasourceConfig):
    """Subsquid datasource config

    :param kind: Always 'evm.node'
    :param url: Ethereum node URL
    :param ws_url: Ethereum node WebSocket URL
    :param http: HTTP client configuration
    :param rollback_depth: A number of blocks to store in database for rollback
    """

    kind: Literal['evm.node']
    url: Url
    ws_url: WsUrl | None = None
    http: HttpConfig | None = None
    rollback_depth: int = 32

    @property
    def merge_subscriptions(self) -> bool:
        return False
