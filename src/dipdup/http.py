import asyncio
import hashlib
import logging
import platform
from contextlib import suppress
from http import HTTPStatus
from json import JSONDecodeError
from pathlib import Path
from typing import Any
from typing import Mapping
from typing import Optional
from typing import Tuple
from typing import cast

import aiohttp
import orjson
from aiolimiter import AsyncLimiter

from dipdup import __version__
from dipdup.config import HTTPConfig
from dipdup.exceptions import InvalidRequestError
from dipdup.prometheus import Metrics

safe_exceptions = (
    aiohttp.ClientConnectionError,
    aiohttp.ClientConnectorError,
    aiohttp.ClientResponseError,
    aiohttp.ClientPayloadError,
)


class HTTPGateway:
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

    @property
    def url(self) -> str:
        """HTTP endpoint URL"""
        return self._http._url

    async def request(
        self,
        method: str,
        url: str,
        weight: int = 1,
        **kwargs,
    ) -> Any:
        """Send arbitrary HTTP request"""
        return await self._http.request(method, url, weight, **kwargs)

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
        self._ratelimiter = (
            AsyncLimiter(max_rate=config.ratelimit_rate, time_period=config.ratelimit_period)
            if config.ratelimit_rate and config.ratelimit_period
            else None
        )
        self.__session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self) -> None:
        """Create underlying aiohttp session"""
        self.__session = aiohttp.ClientSession(
            json_serialize=lambda *a, **kw: orjson.dumps(*a, **kw).decode(),
            connector=aiohttp.TCPConnector(limit=self._config.connection_limit or 100),
            timeout=aiohttp.ClientTimeout(connect=self._config.connection_timeout or 60),
        )

    async def __aexit__(self, exc_type, exc, tb):
        """Close underlying aiohttp session"""
        self._logger.debug('Closing gateway session (%s)', self._url)
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

    # TODO: Move to separate method to cover SignalR negotiations too
    async def _retry_request(
        self,
        method: str,
        url: str,
        weight: int = 1,
        **kwargs,
    ):
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
                if isinstance(e, aiohttp.ClientResponseError):
                    if Metrics.enabled:
                        Metrics.set_http_error(self._url, e.status)

                    if e.status == HTTPStatus.TOO_MANY_REQUESTS:
                        # NOTE: Sleep at least 5 seconds on ratelimit
                        ratelimit_sleep = 5
                        # TODO: Parse Retry-After in UTC date format
                        with suppress(KeyError, ValueError):
                            e.headers = cast(Mapping, e.headers)
                            ratelimit_sleep = int(e.headers['Retry-After'])
                else:
                    if Metrics.enabled:
                        Metrics.set_http_error(self._url, 0)

                self._logger.warning('HTTP request attempt %s/%s failed: %s', attempt, retry_count_str, e)
                self._logger.info('Waiting %s seconds before retry', ratelimit_sleep or retry_sleep)
                await asyncio.sleep(ratelimit_sleep or retry_sleep)
                attempt += 1
                multiplier = 1 if ratelimit_sleep else self._config.retry_multiplier or 1
                retry_sleep *= multiplier

    async def _request(
        self,
        method: str,
        url: str,
        weight: int = 1,
        **kwargs,
    ):
        """Wrapped aiohttp call with preconfigured headers and ratelimiting"""
        if not url.startswith(self._url):
            url = self._url + '/' + url.lstrip('/')

        headers = kwargs.pop('headers', {})
        headers['User-Agent'] = self.user_agent

        params = kwargs.get('params', {})
        params_string = '&'.join(f'{k}={v}' for k, v in params.items())
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
            if response.status == HTTPStatus.NO_CONTENT:
                raise InvalidRequestError('204 No Content', request_string)
            with suppress(JSONDecodeError, aiohttp.ContentTypeError):
                return await response.json()
            return await response.read()

    async def _replay_request(
        self,
        method: str,
        url: str,
        weight: int = 1,
        **kwargs,
    ):
        if not self._config.replay_path:
            raise RuntimeError('Replay path is not set')

        replay_path = Path(self._config.replay_path).expanduser()
        replay_path.mkdir(parents=True, exist_ok=True)

        request_hash = hashlib.sha256(
            f'{self._url} {method} {url} {kwargs}'.encode(),
        ).hexdigest()
        replay_path = Path(self._config.replay_path) / request_hash

        if replay_path.exists():
            if not replay_path.stat().st_size:
                return None
            return orjson.loads(replay_path.read_bytes())

        response = await self._retry_request(method, url, weight, **kwargs)
        with suppress(OSError):
            replay_path.touch(exist_ok=True)
            replay_path.write_bytes(orjson.dumps(response))
        return response

    async def request(
        self,
        method: str,
        url: str,
        weight: int = 1,
        **kwargs,
    ) -> Any:
        """Performs an HTTP request."""
        if self._config.replay_path:
            return await self._replay_request(method, url, weight, **kwargs)
        else:
            return await self._retry_request(method, url, weight, **kwargs)

    def set_user_agent(self, *args: str) -> None:
        """Add list of arguments to User-Agent header"""
        self._user_agent_args = args
        self._user_agent = None
