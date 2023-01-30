from typing import Literal

from pydantic.dataclasses import dataclass

from dipdup import baking_bad
from dipdup.config import DatasourceConfig
from dipdup.config import HTTPConfig
from dipdup.models.metadata import MetadataNetwork


@dataclass
class MetadataDatasourceConfig(DatasourceConfig):
    """DipDup Metadata datasource config

    :param kind: always 'metadata'
    :param network: Network name, e.g. mainnet, ghostnet, etc.
    :param url: GraphQL API URL, e.g. https://metadata.dipdup.net
    :param http: HTTP client configuration
    """

    kind: Literal['metadata']
    network: MetadataNetwork
    url: str = baking_bad.METADATA_API_URL
    http: HTTPConfig | None = None

    def __hash__(self) -> int:
        return hash(self.kind + self.url + self.network.value)
