import logging
from typing import Any, Dict, List, Optional

from dipdup.config import HTTPConfig
from dipdup.datasources.proxy import HTTPRequestProxy

TOKENS_REQUEST_LIMIT = 10


class BcdDatasource:
    def __init__(
        self,
        url: str,
        network: str,
        http_config: Optional[HTTPConfig] = None,
    ) -> None:
        if http_config is None:
            http_config = HTTPConfig()

        self._url = url.rstrip('/')
        self._network = network
        self._proxy = HTTPRequestProxy(http_config)
        self._logger = logging.getLogger('dipdup.bcd')

    async def close_session(self) -> None:
        await self._proxy.close_session()

    async def run(self) -> None:
        pass

    async def resync(self) -> None:
        pass

    async def get_tokens(self, address: str) -> List[Dict[str, Any]]:
        tokens, offset = [], 0
        while True:
            tokens_batch = await self._proxy.http_request(
                'get',
                url=f'{self._url}/v1/contract/{self._network}/{address}/tokens?offset={offset}',
            )
            tokens += tokens_batch
            offset += TOKENS_REQUEST_LIMIT
            if len(tokens_batch) < TOKENS_REQUEST_LIMIT:
                break
        return tokens

    async def get_token(self, address: str, token_id: int) -> Dict[str, Any]:
        return await self._proxy.http_request(
            'get',
            url=f'{self._url}/v1/contract/{self._network}/{address}/tokens?token_id={token_id}',
        )
