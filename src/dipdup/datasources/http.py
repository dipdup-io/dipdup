from typing import Any

from aiohttp.hdrs import METH_GET

from dipdup.config.http import HttpDatasourceConfig
from dipdup.datasources import Datasource


class HttpDatasource(Datasource[HttpDatasourceConfig]):
    async def get(self, url: str, weight: int = 1, **kwargs: Any) -> Any:
        return await self.request(METH_GET, url, weight, **kwargs)

    async def run(self) -> None:
        pass
