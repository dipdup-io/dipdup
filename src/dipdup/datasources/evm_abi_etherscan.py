import logging
from typing import Any
from typing import cast

from dipdup.config import HttpConfig
from dipdup.config.evm_abi_etherscan import API_URL
from dipdup.datasources import Datasource


class AbiEtherscanDatasource(Datasource):
    _default_http_config = HttpConfig(
        ratelimit_rate=5,
        ratelimit_period=1,
    )

    def __init__(self, url: str = API_URL, api_key: str | None = None, http_config: HttpConfig | None = None) -> None:
        super().__init__(url, http_config)
        self._api_key = api_key
        self._logger = logging.getLogger('dipdup.coinbase')

    async def run(self) -> None:
        pass

    async def get_abi(self, address: str) -> dict[str, Any]:
        params = {
            'module': 'contract',
            'action': 'getabi',
            'address': address,
        }
        if self._api_key:
            params['apikey'] = self._api_key

        response = await self.request(
            'get',
            url='abi',
            params=params,
        )
        return cast(dict[str, Any], response['result'])
