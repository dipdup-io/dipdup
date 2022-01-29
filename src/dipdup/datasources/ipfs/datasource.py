from typing import Any

from dipdup.config import HTTPConfig
from dipdup.datasources.datasource import Datasource


class IpfsDatasource(Datasource):
    _default_http_config = HTTPConfig(
        retry_count=1,
    )

    async def run(self) -> None:
        pass

    async def get(self, path: str) -> Any:
        """Download IPFS file by path"""
        return await self._http.request('get', url=path)
