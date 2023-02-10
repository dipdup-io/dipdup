from typing import Literal

from pydantic.dataclasses import dataclass

from dipdup.config import HttpConfig
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
    http: HttpConfig | None = None

    def __hash__(self) -> int:
        return hash(self.kind + self.url + (self.node_url or ''))
