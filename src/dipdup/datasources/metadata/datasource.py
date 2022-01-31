import logging
from typing import Any
from typing import Dict
from typing import Optional

from dipdup.config import HTTPConfig
from dipdup.datasources.datasource import GraphQLDatasource
from dipdup.datasources.metadata.enums import MetadataNetwork


class MetadataDatasource(GraphQLDatasource):
    _default_http_config = HTTPConfig(
        cache=True,
        retry_count=3,
        retry_sleep=1,
        ratelimit_rate=10,
        ratelimit_period=1,
    )

    def __init__(self, url: str, network: MetadataNetwork, http_config: Optional[HTTPConfig] = None) -> None:
        super().__init__(url, self._default_http_config.merge(http_config))
        self._logger = logging.getLogger('dipdup.metadata')
        self._network = network

    async def get_contract_metadata(self, address: str) -> Optional[Dict[str, Any]]:
        response = await self.request(
            'get',
            url='api/rest/contract_metadata',
            params={
                'network': self._network.value,
                'contract': address,
            },
        )
        response = response['contract_metadata']
        if response:
            return response[0]['metadata']
        return None

    async def get_token_metadata(self, address: str, token_id: int) -> Optional[Dict[str, Any]]:
        response = await self.request(
            'get',
            url='api/rest/token_metadata',
            params={
                'network': self._network.value,
                'contract': address,
                'token_id': token_id,
            },
        )
        response = response['token_metadata']
        if response:
            return response[0]['metadata']
        return None

    async def run(self) -> None:
        pass
