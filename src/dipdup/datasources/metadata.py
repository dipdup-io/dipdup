from typing import Any
from typing import cast

from dipdup.config import HttpConfig
from dipdup.config.tzip_metadata import TzipMetadataDatasourceConfig
from dipdup.datasources import Datasource


class TzipMetadataDatasource(Datasource[TzipMetadataDatasourceConfig]):
    _default_http_config = HttpConfig(
        retry_sleep=1,
        retry_multiplier=1.1,
        retry_count=10,
        ratelimit_rate=10,
        ratelimit_period=1,
    )

    async def get_contract_metadata(self, address: str) -> dict[str, Any] | None:
        response = await self.request(
            'get',
            url='api/rest/contract_metadata',
            params={
                'network': self._config.network.value,
                'contract': address,
            },
        )
        response = response['contract_metadata']
        if response:
            return cast(dict[str, Any], response[0]['metadata'])
        return None

    async def get_token_metadata(self, address: str, token_id: int) -> dict[str, Any] | None:
        response = await self.request(
            'get',
            url='api/rest/token_metadata',
            params={
                'network': self._config.network.value,
                'contract': address,
                'token_id': token_id,
            },
        )
        response = response['token_metadata']
        if response:
            return cast(
                dict[str, Any],
                response[0]['metadata'],
            )
        return None

    async def run(self) -> None:
        pass
