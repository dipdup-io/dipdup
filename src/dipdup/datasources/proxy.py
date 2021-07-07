import asyncio
import hashlib
import logging
import pickle
from typing import Optional

import aiohttp
from aiolimiter import AsyncLimiter
from fcache.cache import FileCache  # type: ignore

from dipdup.config import DEFAULT_RETRY_COUNT, DEFAULT_RETRY_SLEEP  # type: ignore
from dipdup.utils import http_request


class DatasourceRequestProxy:
    """Wrapper for datasource HTTP requests.

    Covers caching, retrying failed requests and ratelimiting"""

    def __init__(
        self,
        cache: bool = False,
        retry_count: int = DEFAULT_RETRY_COUNT,
        retry_sleep: int = DEFAULT_RETRY_SLEEP,
        ratelimiter: Optional[AsyncLimiter] = None,
    ) -> None:
        self._logger = logging.getLogger(__name__)
        self._cache = FileCache('dipdup', flag='cs') if cache else None
        self._retry_count = retry_count
        self._retry_sleep = retry_sleep
        self._ratelimiter = ratelimiter
        self._session = aiohttp.ClientSession()

    async def _wrapped_request(self, method: str, **kwargs):
        for attempt in range(self._retry_count):
            self._logger.debug('Datasource request attempt %s/%s', attempt + 1, self._retry_count)
            try:
                return await http_request(self._session, method, **kwargs)
            except (aiohttp.ClientConnectionError, aiohttp.ClientConnectorError) as e:
                if attempt + 1 == self._retry_count:
                    raise e
                self._logger.warning('Datasource request failed: %s', e)
                await asyncio.sleep(self._retry_sleep)

    async def http_request(self, method: str, skip_cache: bool = False, weight: int = 1, **kwargs):
        if self._cache is not None and not skip_cache:
            key = hashlib.sha256(pickle.dumps([method, kwargs])).hexdigest()
            try:
                return self._cache[key]
            except KeyError:
                if self._ratelimiter:
                    await self._ratelimiter.acquire(weight)
                response = await self._wrapped_request(method, **kwargs)
                self._cache[key] = response
                return response
        else:
            if self._ratelimiter:
                await self._ratelimiter.acquire(weight)
            response = await self._wrapped_request(method, **kwargs)
            return response

    async def close_session(self) -> None:
        await self._session.close()
