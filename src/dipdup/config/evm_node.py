from typing import Literal

from pydantic import validator
from pydantic.dataclasses import dataclass

from dipdup.config import HttpConfig
from dipdup.config import IndexDatasourceConfig


@dataclass
class EvmNodeDatasourceConfig(IndexDatasourceConfig):
    """Subsquid datasource config

    :param kind: always 'evm.node'
    :param url: URL of Subsquid archive API
    :param node_url: URL of Ethereum node
    :param http: HTTP client configuration
    :param rollback_depth: Number of blocks to keep in the database
    """

    kind: Literal['evm.node']
    url: str
    ws_url: str
    http: HttpConfig | None = None
    rollback_depth: int = 32

    @property
    def merge_subscriptions(self) -> bool:
        return False

    # FIXME: Update validators
    @validator('url', allow_reuse=True)
    def _valid_url(cls, v: str) -> str:
        if not v.startswith(('http', 'https')):
            raise ValueError('Node URL must start with http(s) or ws(s)')
        return v
