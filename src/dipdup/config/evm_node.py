from __future__ import annotations

from typing import Literal

from pydantic import validator
from pydantic.dataclasses import dataclass

from dipdup.config import HttpConfig
from dipdup.config import IndexDatasourceConfig
from dipdup.exceptions import ConfigurationError


@dataclass
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

    @validator('url')
    def _valid_url(cls, v: str) -> str:
        if not v.startswith(('http://', 'https://')):
            raise ConfigurationError('Ethereum node URL must start with http(s)://')
        return v

    @validator('ws_url')
    def _valid_ws_url(cls, v: str | None) -> str | None:
        if v and not v.startswith(('ws://', 'wss://')):
            raise ConfigurationError('Ethereum node WebSocket URL must start with ws(s)://')
        return v
