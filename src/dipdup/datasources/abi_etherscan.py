import asyncio
from typing import Any
from typing import cast

import orjson

from dipdup.config import HttpConfig
from dipdup.config.abi_etherscan import EtherscanDatasourceConfig
from dipdup.datasources import AbiDatasource
from dipdup.exceptions import DatasourceError


class EtherscanDatasource(AbiDatasource[EtherscanDatasourceConfig]):
    _default_http_config = HttpConfig(
        ratelimit_rate=1,
        ratelimit_period=5,
        ratelimit_sleep=15,
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

        for _ in range(self._http_config.retry_count):
            response = await self.request(
                'get',
                url='',
                params=params,
            )
            if message := response.get('message'):
                self._logger.info(message)

            if result := response.get('result'):
                if isinstance(result, str) and 'rate limit reached' in result:
                    self._logger.warning('Ratelimited; sleeping %s seconds', self._http_config.ratelimit_sleep)
                    await asyncio.sleep(self._http_config.retry_sleep)
                    continue

                return cast(dict[str, Any], orjson.loads(result))

        raise DatasourceError(message, self.name)
