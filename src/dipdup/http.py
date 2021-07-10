import asyncio
import hashlib
import logging
import pickle
from abc import ABC, abstractmethod
from typing import Optional, Tuple

import aiohttp
from aiolimiter import AsyncLimiter
from fcache.cache import FileCache  # type: ignore

from dipdup import __version__
from dipdup.config import HTTPConfig  # type: ignore


class HTTPGateway(ABC):
    def __init__(self, url: str, http_config: Optional[HTTPConfig] = None) -> None:
        self._http_config = self._default_http_config()
        self._http_config.merge(http_config)
        self._http = _HTTPGateway(url.rstrip('/'), self._http_config)

    @abstractmethod
    def _default_http_config(self) -> HTTPConfig:
        ...

    async def close_session(self) -> None:
        await self._http.close_session()

    def set_user_agent(self, *args: str) -> None:
        self._http.set_user_agent(*args)


class _HTTPGateway:
    """Wrapper for aiohttp HTTP requests.

    Covers caching, retrying failed requests and ratelimiting"""

    def __init__(self, url: str, config: HTTPConfig) -> None:
        self._logger = logging.getLogger('dipdup.http')
        self._url = url
        self._config = config
        self._user_agent_args: Tuple[str, ...] = ()
        self._cache = FileCache('dipdup', flag='cs')
        self._ratelimiter = (
            AsyncLimiter(max_rate=config.ratelimit_rate, time_period=config.ratelimit_period)
            if config.ratelimit_rate and config.ratelimit_period
            else None
        )
        self._session = aiohttp.ClientSession()

    async def _wrapped_request(self, method: str, url: str, **kwargs):
        attempts = list(range(self._config.retry_count)) if self._config.retry_count else [0]
        for attempt in attempts:
            self._logger.debug('HTTP request attempt %s/%s', attempt + 1, self._config.retry_count)
            try:
                return await self._request(
                    method=method,
                    url=url,
                    **kwargs,
                )
            except (aiohttp.ClientConnectionError, aiohttp.ClientConnectorError) as e:
                if attempt + 1 == attempts[-1]:
                    raise e
                self._logger.warning('HTTP request failed: %s', e)
                await asyncio.sleep(self._config.retry_sleep or 0)

    async def _request(self, method: str, url: str, **kwargs):
        """Wrapped aiohttp call with preconfigured headers and logging"""
        user_agent = f'dipdup/{__version__} '
        if self._user_agent_args:
            user_agent += f" ({', '.join(self._user_agent_args)})"
        user_agent += aiohttp.http.SERVER_SOFTWARE
        headers = {
            **kwargs.pop('headers', {}),
            'User-Agent': user_agent,
        }
        if not url.startswith(self._url):
            url = self._url + '/' + url.lstrip('/')
        params = kwargs.get('params', {})
        params_string = '&'.join([f'{k}={v}' for k, v in params.items()])
        request_string = f'{url}?{params_string}'.rstrip('?')
        self._logger.debug('Calling `%s`', request_string)
        async with self._session.request(
            method=method,
            url=url,
            headers=headers,
            **kwargs,
        ) as response:
            return await response.json()

    async def request(self, method: str, url: str, cache: bool = False, weight: int = 1, **kwargs):
        if self._config.cache and cache:
            key = hashlib.sha256(pickle.dumps([method, url, kwargs])).hexdigest()
            try:
                return self._cache[key]
            except KeyError:
                if self._ratelimiter:
                    await self._ratelimiter.acquire(weight)
                response = await self._wrapped_request(method, url, **kwargs)
                self._cache[key] = response
                return response
        else:
            if self._ratelimiter:
                await self._ratelimiter.acquire(weight)
            response = await self._wrapped_request(method, url, **kwargs)
            return response

    async def close_session(self) -> None:
        await self._session.close()

    async def set_user_agent(self, *args: str) -> None:
        self._user_agent_args = args
