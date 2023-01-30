import logging
from typing import Any

from aiohttp.hdrs import METH_GET

from dipdup.config import HTTPConfig
from dipdup.datasources import Datasource

_logger = logging.getLogger('dipdup.http')


class HttpDatasource(Datasource):
    def __init__(self, url: str, http_config: HTTPConfig | None = None) -> None:
        super().__init__(url, http_config)
        self._logger = _logger

    async def get(self, url: str, weight: int = 1, **kwargs: Any) -> Any:
        return await self.request(METH_GET, url, weight, **kwargs)

    async def run(self) -> None:
        pass
