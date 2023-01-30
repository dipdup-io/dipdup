from dataclasses import field
from typing import Literal

from pydantic.dataclasses import dataclass

from dipdup.config import DatasourceConfig
from dipdup.config import HTTPConfig


@dataclass
class CoinbaseDatasourceConfig(DatasourceConfig):
    """Coinbase datasource config

    :param kind: always 'coinbase'
    :param api_key: API key
    :param secret_key: API secret key
    :param passphrase: API passphrase
    :param http: HTTP client configuration
    """

    kind: Literal['coinbase']
    api_key: str | None = None
    secret_key: str | None = field(default=None, repr=False)
    passphrase: str | None = field(default=None, repr=False)

    http: HTTPConfig | None = None

    def __hash__(self) -> int:
        return hash(self.kind)
