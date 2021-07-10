import logging
from typing import Any, Dict, List, Optional

from dipdup.config import HTTPConfig
from dipdup.http import HTTPGateway


class BcdDatasource(HTTPGateway):
    def __init__(
        self,
        url: str,
        network: str,
        http_config: Optional[HTTPConfig] = None,
    ) -> None:
        super().__init__(url, http_config)
        self._logger = logging.getLogger('dipdup.bcd')
        self._network = network

    async def run(self) -> None:
        pass

    async def resync(self) -> None:
        pass

    async def get_tokens(self, address: str) -> List[Dict[str, Any]]:
        return await self._http.request(
            'get',
            url=f'v1/contract/{self._network}/{address}/tokens',
        )

    def _default_http_config(self) -> HTTPConfig:
        return HTTPConfig(
            cache=True,
            retry_count=3,
            retry_sleep=1,
            ratelimit_rate=100,
            ratelimit_period=30,
        )

    cache: Optional[bool] = None
    retry_count: Optional[int] = None
    retry_sleep: Optional[int] = None
    ratelimit_rate: Optional[int] = None
    ratelimit_period: Optional[int] = None
