from typing import Literal

from pydantic.dataclasses import dataclass

from dipdup import baking_bad
from dipdup.config import DatasourceConfig
from dipdup.config import HttpConfig
from dipdup.models.tzip_metadata import TzipMetadataNetwork


@dataclass
class TzipMetadataDatasourceConfig(DatasourceConfig):
    """DipDup Metadata datasource config

    :param kind: always 'tzip_metadata'
    :param network: Network name, e.g. mainnet, ghostnet, etc.
    :param url: GraphQL API URL, e.g. https://metadata.dipdup.net
    :param http: HTTP client configuration
    """

    kind: Literal['tzip_metadata']
    network: TzipMetadataNetwork
    url: str = baking_bad.METADATA_API_URL
    http: HttpConfig | None = None

    def __hash__(self) -> int:
        return hash(self.kind + self.url + self.network.value)
