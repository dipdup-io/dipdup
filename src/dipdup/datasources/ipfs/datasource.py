import logging
from typing import Any
from typing import Optional

from dipdup.config import HTTPConfig
from dipdup.datasources.datasource import Datasource


class IpfsDatasource(Datasource):
    _default_http_config = HTTPConfig(
        retry_sleep=1,
        retry_multiplier=1.1,
        retry_count=10,
    )

    def __init__(self, url: str, http_config: Optional[HTTPConfig] = None) -> None:
        super().__init__(url, self._default_http_config.merge(http_config))
        self._logger = logging.getLogger('dipdup.ipfs')

    async def run(self) -> None:
        pass

    async def get(self, path: str) -> Any:
        """Download IPFS file by path"""
        return await self._http.request('get', url=path)
