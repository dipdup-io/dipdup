from typing import Any
from typing import cast

from dipdup.config import HttpConfig
from dipdup.config.evm_abi_etherscan import AbiEtherscanDatasourceConfig
from dipdup.datasources import Datasource


class AbiEtherscanDatasource(Datasource[AbiEtherscanDatasourceConfig]):
    _default_http_config = HttpConfig(
        ratelimit_rate=5,
        ratelimit_period=1,
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
            url='abi',
            params=params,
        )
        return cast(dict[str, Any], response['result'])
