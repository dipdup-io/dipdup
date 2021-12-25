import asyncio
import hashlib
import logging
import pickle
import platform
from abc import ABC
from contextlib import suppress
from http import HTTPStatus
from typing import Mapping
from typing import Optional
from typing import Tuple
from typing import cast

import aiohttp
from aiolimiter import AsyncLimiter
from fcache.cache import FileCache  # type: ignore

from dipdup import __version__
from dipdup.config import HTTPConfig  # type: ignore

safe_exceptions = (
    aiohttp.ClientConnectionError,
    aiohttp.ClientConnectorError,
    aiohttp.ClientResponseError,
    aiohttp.ClientPayloadError,
)


class HTTPGateway(ABC):
    """Base class for datasources which connect to remote HTTP endpoints"""

    _default_http_config: HTTPConfig

    def __init__(self, url: str, http_config: HTTPConfig) -> None:
        self._http_config = http_config
        self._http = _HTTPGateway(url.rstrip('/'), self._http_config)

    async def __aenter__(self) -> None:
        """Create underlying aiohttp session"""
        await self._http.__aenter__()

    async def __aexit__(self, exc_type, exc, tb) -> None:
        """Close underlying aiohttp session"""
        await self._http.__aexit__(exc_type, exc, tb)

    async def close_session(self) -> None:
        """Close aiohttp session"""
        await self._http.close_session()

    def set_user_agent(self, *args: str) -> None:
        """Add list of arguments to User-Agent header"""
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
        """Create underlying aiohttp session"""
        self.__session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit=self._config.connection_limit or 100),
            timeout=aiohttp.ClientTimeout(connect=self._config.connection_timeout or 60),
        )

    async def __aexit__(self, exc_type, exc, tb):
        """Close underlying aiohttp session"""
        self._logger.info('Closing gateway session (%s)', self._url)
        await self.__session.close()

    @property
    def user_agent(self) -> str:
        """Return User-Agent header compiled from aiohttp's one and dipdup environment"""
        if self._user_agent is None:
            user_agent_args = (platform.system(), platform.machine()) + (self._user_agent_args or ())
            user_agent = f'dipdup/{__version__} ({"; ".join(user_agent_args)})'
            user_agent += ' ' + aiohttp.http.SERVER_SOFTWARE
            self._user_agent = user_agent
        return self._user_agent

    @property
    def _session(self) -> aiohttp.ClientSession:
        """Get an aiohttp session from inside of it's context manager"""
        if self.__session is None:
            raise RuntimeError('aiohttp session is not initialized. Wrap with `async with httpgateway_instance`')
        if self.__session.closed:
            raise RuntimeError('aiohttp session is closed')
        return self.__session

    async def _retry_request(self, method: str, url: str, weight: int = 1, **kwargs):
        """Retry a request in case of failure sleeping according to config"""
        attempt = 1
        retry_sleep = self._config.retry_sleep or 0
        retry_count = self._config.retry_count
        retry_count_str = str(retry_count or 'inf')

        while True:
            self._logger.debug('HTTP request attempt %s/%s', attempt, retry_count_str)
            try:
                return await self._request(
                    method=method,
                    url=url,
                    weight=weight,
                    **kwargs,
                )
            except safe_exceptions as e:
                if self._config.retry_count and attempt - 1 == self._config.retry_count:
                    raise e

                ratelimit_sleep: Optional[float] = None
                if isinstance(e, aiohttp.ClientResponseError) and e.status == HTTPStatus.TOO_MANY_REQUESTS:
                    # NOTE: Sleep at least 5 seconds on ratelimit
                    ratelimit_sleep = 5
                    # TODO: Parse Retry-After in UTC date format
                    with suppress(KeyError, ValueError):
                        e.headers = cast(Mapping, e.headers)
                        ratelimit_sleep = int(e.headers['Retry-After'])

                self._logger.warning('HTTP request attempt %s/%s failed: %s', attempt, retry_count_str, e)
                self._logger.info('Waiting %s seconds before retry', ratelimit_sleep or retry_sleep)
                await asyncio.sleep(ratelimit_sleep or retry_sleep)
                attempt += 1
                multiplier = 1 if ratelimit_sleep else self._config.retry_multiplier or 1
                retry_sleep *= multiplier

    async def _request(self, method: str, url: str, weight: int = 1, **kwargs):
        """Wrapped aiohttp call with preconfigured headers and ratelimiting"""
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

        if self._ratelimiter:
            await self._ratelimiter.acquire(weight)

        async with self._session.request(
            method=method,
            url=url,
            headers=headers,
            raise_for_status=True,
            **kwargs,
        ) as response:
            return await response.json()

    async def request(self, method: str, url: str, cache: bool = False, weight: int = 1, **kwargs):
        """Perform an HTTP request.

        Check for parameters in cache, if not found, perform retried request and cache result.
        """
        if self._config.cache and cache:
            key = hashlib.sha256(pickle.dumps([method, url, kwargs])).hexdigest()
            try:
                return self._cache[key]
            except KeyError:
                response = await self._retry_request(method, url, weight, **kwargs)
                self._cache[key] = response
                return response
        else:
            response = await self._retry_request(method, url, weight, **kwargs)
            return response

    async def close_session(self) -> None:
        """Close aiohttp session"""
        await self._session.close()

    def set_user_agent(self, *args: str) -> None:
        """Add list of arguments to User-Agent header"""
        self._user_agent_args = args
        self._user_agent = None
