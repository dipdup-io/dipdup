from typing import Literal

from pydantic.dataclasses import dataclass

from dipdup.config import DatasourceConfig
from dipdup.config import HttpConfig

API_URL = 'https://api.etherscan.io/api'


@dataclass
class EtherscanDatasourceConfig(DatasourceConfig):
    """Coinbase datasource config

    :param kind: always 'evm.abi_etherscan'
    :param url: API URL
    :param api_key: API key
    """

    kind: Literal['evm.abi_etherscan']
    url: str = API_URL
    api_key: str | None = None

    http: HttpConfig | None = None

    def __hash__(self) -> int:
        return hash(self.kind)
