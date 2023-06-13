from typing import Any

from dipdup.config import HttpConfig
from dipdup.config.ipfs import IpfsDatasourceConfig
from dipdup.datasources import Datasource


class IpfsDatasource(Datasource[IpfsDatasourceConfig]):
    _default_http_config = HttpConfig()

    async def run(self) -> None:
        pass

    async def get(self, path: str) -> Any:
        """Download IPFS file by path"""
        return await self._http.request('get', url=path)
