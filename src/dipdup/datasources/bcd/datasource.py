import logging
from typing import Any, Dict, List

from dipdup.datasources.proxy import DatasourceRequestProxy
from dipdup.datasources.tzkt.datasource import Address


class BcdDatasource:
    def __init__(self, url: str, cache: bool):
        super().__init__()
        self._url = url.rstrip('/')
        self._logger = logging.getLogger(__name__)
        self._proxy = DatasourceRequestProxy(cache)

    async def get_tokens(self, address: Address) -> List[Dict[str, Any]]:
        return await self._proxy.http_request(
            'get',
            url=f'{self._url}/v1/contracts/{address}',
        )
