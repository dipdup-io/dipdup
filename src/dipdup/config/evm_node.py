from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict
from pydantic import field_validator
from pydantic.dataclasses import dataclass

from dipdup.config import HttpConfig
from dipdup.config import IndexDatasourceConfig


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
    url: str
    ws_url: str | None = None
    http: HttpConfig | None = None
    rollback_depth: int = 32

    @property
    def merge_subscriptions(self) -> bool:
        return False

    @field_validator('url')
    @classmethod
    def _valid_url(cls, v: str) -> str:
        if not v.startswith(('http://', 'https://')):
            raise ValueError('Ethereum node URL must start with http(s)://')
        return v

    @field_validator('ws_url')
    @classmethod
    def _valid_ws_url(cls, v: str | None) -> str | None:
        if v and not v.startswith(('ws://', 'wss://')):
            raise ValueError('Ethereum node WebSocket URL must start with ws(s)://')
        return v
