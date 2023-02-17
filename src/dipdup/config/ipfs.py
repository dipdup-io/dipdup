from typing import Literal

from pydantic.dataclasses import dataclass

from dipdup.config import DEFAULT_IPFS_URL
from dipdup.config import DatasourceConfig
from dipdup.config import HttpConfig


@dataclass
class IpfsDatasourceConfig(DatasourceConfig):
    """IPFS datasource config

    :param kind: always 'ipfs'
    :param url: IPFS node URL, e.g. https://ipfs.io/ipfs/
    :param http: HTTP client configuration
    """

    kind: Literal['ipfs']
    url: str = DEFAULT_IPFS_URL
    http: HttpConfig | None = None