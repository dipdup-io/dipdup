import asyncio
import hashlib
import logging
import pickle
from typing import Optional

import aiohttp
from aiolimiter import AsyncLimiter
from fcache.cache import FileCache  # type: ignore

from dipdup.config import HTTPConfig  # type: ignore
from dipdup.utils import http_request


class HTTPRequestProxy:
    """Wrapper for aiohttp HTTP requests.

    Covers caching, retrying failed requests and ratelimiting"""

    def __init__(self, config: Optional[HTTPConfig] = None) -> None:
        if config is None:
            config = HTTPConfig()
        self._logger = logging.getLogger(__name__)
        self._config = config
        self._cache = FileCache('dipdup', flag='cs')
        self._ratelimiter = (
            AsyncLimiter(max_rate=config.ratelimit_rate, time_period=config.ratelimit_period)
            if config.ratelimit_rate and config.ratelimit_period
            else None
        )
        self._session = aiohttp.ClientSession()

    async def _wrapped_request(self, method: str, **kwargs):
        for attempt in range(self._config.retry_count):
            self._logger.debug('HTTP request attempt %s/%s', attempt + 1, self._config.retry_count)
            try:
                return await http_request(self._session, method, **kwargs)
            except (aiohttp.ClientConnectionError, aiohttp.ClientConnectorError) as e:
                if attempt + 1 == self._config.retry_count:
                    raise e
                self._logger.warning('HTTP request failed: %s', e)
                await asyncio.sleep(self._config.retry_sleep)

    async def http_request(self, method: str, cache: bool = False, weight: int = 1, **kwargs):
        if self._config.cache and cache:
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
