from typing import Literal

from pydantic import validator
from pydantic.dataclasses import dataclass

from dipdup.config import HttpConfig
from dipdup.config import IndexConfig
from dipdup.config import IndexDatasourceConfig


@dataclass
class SubsquidDatasourceConfig(IndexDatasourceConfig):
    """Subsquid datasource config

    :param kind: always 'evm.subsquid'
    :param url: URL of Subsquid archive API
    :param node_url: URL of Ethereum node
    :param http: HTTP client configuration
    """

    kind: Literal['evm.subsquid']
    url: str
    node_url: str | None = None
    node_ws_url: str | None = None
    http: HttpConfig | None = None

    # FIXME: Update validators
    @validator('url', allow_reuse=True)
    def _valid_url(cls, v: str) -> str:
        if not v.startswith(('http', 'https')):
            raise ValueError('Node URL must start with http(s) or ws(s)')
        return v

    @validator('node_url', allow_reuse=True)
    def _valid_node_url(cls, v: str | None) -> str | None:
        if v and not v.startswith(('http', 'https')):
            raise ValueError('Node URL must start with http(s) or ws(s)')
        return v


@dataclass
class SubsquidIndexConfig(IndexConfig):
    datasource: SubsquidDatasourceConfig
