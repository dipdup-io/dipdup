from typing import Literal

from pydantic.dataclasses import dataclass

from dipdup.config import DatasourceConfig
from dipdup.config import HttpConfig


@dataclass
class SubsquidDatasourceConfig(DatasourceConfig):
    """Subsquid datasource config

    :param kind: always 'evm.subsquid'
    :param archive_url: URL of Subsquid archive API
    :param node_url: URL of Ethereum node
    :param http: HTTP client configuration
    """

    kind: Literal['evm.subsquid']
    archive_url: str
    node_url: str | None = None
    http: HttpConfig | None = None

    def __hash__(self) -> int:
        return hash(self.kind + self.archive_url + (self.node_url or ''))
