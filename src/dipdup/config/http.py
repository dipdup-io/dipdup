from typing import Literal

from pydantic.dataclasses import dataclass

from dipdup.config import DatasourceConfig
from dipdup.config import HttpConfig


@dataclass
class HttpDatasourceConfig(DatasourceConfig):
    """Generic HTTP datasource config

    :param kind: always 'http'
    :param url: URL to fetch data from
    :param http: HTTP client configuration
    """

    kind: Literal['http']
    url: str
    http: HttpConfig | None = None
