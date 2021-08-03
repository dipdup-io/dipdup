import asyncio
import hashlib
import logging
import pickle
import platform
from abc import ABC, abstractmethod
from contextlib import suppress
from http import HTTPStatus
from typing import Mapping, Optional, Tuple, cast

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

    async def __aenter__(self) -> None:
        await self._http.__aenter__()

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self._http.__aexit__(exc_type, exc, tb)

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
        self._user_agent: Optional[str] = None
        self._cache = FileCache('dipdup', flag='cs')
        self._ratelimiter = (
            AsyncLimiter(max_rate=config.ratelimit_rate, time_period=config.ratelimit_period)
            if config.ratelimit_rate and config.ratelimit_period
            else None
        )
        self.__session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self) -> None:
        self.__session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit=self._config.connection_limit or 100),
        )

    async def __aexit__(self, exc_type, exc, tb):
        self._logger.info('Closing gateway session (%s)', self._url)
        await self.__session.close()

    @property
    def user_agent(self) -> str:
        if self._user_agent is None:
            user_agent_args = (platform.system(), platform.machine()) + (self._user_agent_args or ())
            user_agent = f'dipdup/{__version__} ({"; ".join(user_agent_args)})'
            user_agent += ' ' + aiohttp.http.SERVER_SOFTWARE
            self._user_agent = user_agent
        return self._user_agent

    @property
    def _session(self) -> aiohttp.ClientSession:
        if not self.__session:
            raise RuntimeError('Session is not initialized. Wrap with `async with`')
        return self.__session

    async def _wrapped_request(self, method: str, url: str, **kwargs):
        attempt = 1
        retry_sleep = self._config.retry_sleep or 0
        while True:
            self._logger.debug('HTTP request attempt %s/%s', attempt, self._config.retry_count or 'inf')
            try:
                return await self._request(
                    method=method,
                    url=url,
                    **kwargs,
                )
            except (aiohttp.ClientConnectionError, aiohttp.ClientConnectorError) as e:
                if self._config.retry_count and attempt - 1 == self._config.retry_count:
                    raise e
                self._logger.warning('HTTP request failed: %s', e)
                await asyncio.sleep(retry_sleep)
                retry_sleep *= self._config.retry_multiplier or 1
            except aiohttp.ClientResponseError as e:
                if e.code == HTTPStatus.TOO_MANY_REQUESTS:
                    ratelimit_sleep = 5
                    # TODO: Parse Retry-After in UTC date format
                    with suppress(KeyError, ValueError):
                        e.headers = cast(Mapping, e.headers)
                        ratelimit_sleep = int(e.headers['Retry-After'])

                    self._logger.warning('HTTP request failed: %s', e)
                    await asyncio.sleep(ratelimit_sleep)
                else:
                    if self._config.retry_count and attempt - 1 == self._config.retry_count:
                        raise e
                    self._logger.warning('HTTP request failed: %s', e)
                    await asyncio.sleep(self._config.retry_sleep or 0)
                    retry_sleep *= self._config.retry_multiplier or 1

    async def _request(self, method: str, url: str, **kwargs):
        """Wrapped aiohttp call with preconfigured headers and logging"""
        headers = {
            **kwargs.pop('headers', {}),
            'User-Agent': self.user_agent,
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
            raise_for_status=True,
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

    def set_user_agent(self, *args: str) -> None:
        self._user_agent_args = args
        self._user_agent = None
