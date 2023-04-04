from typing import Any
from typing import cast

import orjson

from dipdup.config import HttpConfig
from dipdup.config.abi_etherscan import EtherscanDatasourceConfig
from dipdup.datasources import AbiDatasource


class EtherscanDatasource(AbiDatasource[EtherscanDatasourceConfig]):
    _default_http_config = HttpConfig(
        ratelimit_rate=1,
        ratelimit_period=5,
        ratelimit_sleep=5,
    )

    async def run(self) -> None:
        pass

    async def get_abi(self, address: str) -> dict[str, Any]:
        params = {
            'module': 'contract',
            'action': 'getabi',
            'address': address,
        }
        if self._config.api_key:
            params['apikey'] = self._config.api_key

        response = await self.request(
            'get',
            url='',
            params=params,
        )
        return cast(dict[str, Any], orjson.loads(response['result']))
