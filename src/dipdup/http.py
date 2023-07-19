import asyncio
import hashlib
import logging
import platform
import sys
import time
from contextlib import AbstractAsyncContextManager
from contextlib import suppress
from http import HTTPStatus
from json import JSONDecodeError
from pathlib import Path
from typing import Any
from typing import Literal
from typing import Mapping
from typing import Optional
from typing import cast
from typing import overload
from urllib.parse import urlsplit
from urllib.parse import urlunsplit

import aiohttp
import aiohttp.test_utils
import orjson
from aiolimiter import AsyncLimiter

from dipdup import __version__
from dipdup.config import ResolvedHttpConfig
from dipdup.exceptions import FrameworkException
from dipdup.exceptions import InvalidRequestError
from dipdup.performance import metrics
from dipdup.prometheus import Metrics
from dipdup.utils import json_dumps

safe_exceptions = (
    asyncio.TimeoutError,
    aiohttp.ClientConnectionError,
    aiohttp.ClientConnectorError,
    aiohttp.ClientResponseError,
    aiohttp.ClientPayloadError,
)


class HTTPGateway(AbstractAsyncContextManager[None]):
    """Base class for datasources which connect to remote HTTP endpoints"""

    def __init__(self, url: str, http_config: ResolvedHttpConfig) -> None:
        self._http_config = http_config
        self._http = _HTTPGateway(url, self._http_config)

    async def __aenter__(self) -> None:
        """Create underlying aiohttp session"""
        await self._http.__aenter__()

    async def __aexit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any) -> None:
        """Close underlying aiohttp session"""
        await self._http.__aexit__(exc_type, exc_val, exc_tb)

    @property
    def url(self) -> str:
        """HTTP endpoint URL"""
        return self._http._url

    async def request(
        self,
        method: str,
        url: str,
        weight: int = 1,
        **kwargs: Any,
    ) -> Any:
        """Send arbitrary HTTP request"""
        return await self._http.request(method, url, weight, **kwargs)

    def set_user_agent(self, *args: str) -> None:
        """Add list of arguments to User-Agent header"""
        self._http.set_user_agent(*args)


class _HTTPGateway(AbstractAsyncContextManager[None]):
    """Wrapper for aiohttp HTTP requests.

    Covers caching, retrying failed requests and ratelimiting"""

    def __init__(self, url: str, config: ResolvedHttpConfig) -> None:
        self._logger = logging.getLogger(__name__)
        parsed_url = urlsplit(url)
        self._url = urlunsplit((parsed_url.scheme, parsed_url.netloc, '', '', ''))
        self._alias = config.alias or parsed_url.netloc
        self._path = parsed_url.path
        self._config = config
        self._user_agent_args: tuple[str, ...] = ()
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
            base_url=self._url,
            json_serialize=lambda *a, **kw: json_dumps(*a, **kw).decode(),
            connector=aiohttp.TCPConnector(limit=self._config.connection_limit),
            timeout=aiohttp.ClientTimeout(total=self._config.connection_timeout),
        )

    async def __aexit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any) -> None:
        """Close underlying aiohttp session"""
        self._logger.debug('Closing gateway session (%s)', self._url)
        if not self.__session:
            raise FrameworkException('Session is not initialized')
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
        if isinstance(self.__session, aiohttp.test_utils.TestClient):
            return self.__session
        if self.__session is None:
            raise FrameworkException('aiohttp session is not initialized. Wrap with `async with httpgateway_instance`')
        if self.__session.closed:
            raise FrameworkException('aiohttp session is closed')
        return self.__session

    # TODO: Move to separate method to cover SignalR negotiations too
    async def _retry_request(
        self,
        method: str,
        url: str,
        weight: int = 1,
        **kwargs: Any,
    ) -> Any:
        """Retry a request in case of failure sleeping according to config"""
        attempt = 1
        retry_sleep = self._config.retry_sleep
        retry_count = self._config.retry_count
        retry_count_str = 'inf' if retry_count is sys.maxsize else str(retry_count)

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

                ratelimit_sleep: float | None = None
                if isinstance(e, aiohttp.ClientResponseError):
                    if Metrics.enabled:
                        Metrics.set_http_error(self._url, e.status)

                    if e.status == HTTPStatus.TOO_MANY_REQUESTS:
                        ratelimit_sleep = self._config.ratelimit_sleep
                        # TODO: Parse Retry-After in UTC date format
                        with suppress(KeyError, ValueError):
                            e.headers = cast(Mapping[str, Any], e.headers)
                            ratelimit_sleep = max(ratelimit_sleep, int(e.headers['Retry-After']))
                else:
                    if Metrics.enabled:
                        Metrics.set_http_error(self._url, 0)

                self._logger.warning('HTTP request attempt %s/%s failed: %s', attempt, retry_count_str, e)
                self._logger.info('Waiting %s seconds before retry', ratelimit_sleep or retry_sleep)
                await asyncio.sleep(ratelimit_sleep or retry_sleep)
                attempt += 1
                if not ratelimit_sleep:
                    retry_sleep *= self._config.retry_multiplier

    # FIXME: Temporary overload for Subsquid; move to public method
    @overload
    async def _request(
        self,
        method: str,
        url: str,
        weight: int,
        raw: Literal[True],
        **kwargs: Any,
    ) -> aiohttp.ClientResponse:
        ...

    @overload
    async def _request(
        self,
        method: str,
        url: str,
        weight: int,
        raw: Literal[False],
        **kwargs: Any,
    ) -> Any:
        ...

    async def _request(
        self,
        method: str,
        url: str,
        weight: int = 1,
        raw: bool = False,
        **kwargs: Any,
    ) -> Any:
        """Wrapped aiohttp call with preconfigured headers and ratelimiting"""
        metrics and metrics.inc(f'{self._alias}:requests_total', 1.0)
        if not url:
            url = self._path
        elif url.startswith('http'):
            url = url.replace(self._url, '').rstrip('/')
        else:
            url = f"{self._path.rstrip('/')}/{url}"

        headers = kwargs.pop('headers', {})
        headers['User-Agent'] = self.user_agent

        params = kwargs.get('params', {})
        params_string = '&'.join(f'{k}={v}' for k, v in params.items())
        request_string = f'{self._url}{url}?{params_string}'.rstrip('?')
        self._logger.debug('Calling `%s`', request_string)

        if self._ratelimiter:
            await self._ratelimiter.acquire(weight)

        started_at = time.time()

        async with self._session.request(
            method=method,
            url=url,
            headers=headers,
            raise_for_status=True,
            **kwargs,
        ) as response:
            await response.read()
            metrics and metrics.inc(f'{self._alias}:time_in_requests', (time.time() - started_at) / 60)
            if raw:
                return response

            # NOTE: Use raw=True if fail on 204 is not a desired behavior
            if response.status == HTTPStatus.NO_CONTENT:
                raise InvalidRequestError('204 No Content', request_string)
            with suppress(JSONDecodeError):
                return orjson.loads(response._body)
            return response._body

    async def _replay_request(
        self,
        method: str,
        url: str,
        weight: int = 1,
        **kwargs: Any,
    ) -> Any:
        if not self._config.replay_path:
            raise FrameworkException('Replay path is not set')

        replay_path = Path(self._config.replay_path).expanduser()
        replay_path.mkdir(parents=True, exist_ok=True)

        request_hash = hashlib.sha256(
            f'{self._url} {method} {self._path}/{url} {kwargs}'.encode(),
        ).hexdigest()
        replay_path = Path(self._config.replay_path).joinpath(request_hash).expanduser()

        if replay_path.exists():
            if not replay_path.stat().st_size:
                return None

            content = replay_path.read_bytes()
            with suppress(JSONDecodeError):
                return orjson.loads(content)
            return content

        response = await self._retry_request(method, url, weight, **kwargs)
        replay_path.touch(exist_ok=True)
        if isinstance(response, bytes):
            replay_path.write_bytes(response)
        else:
            replay_path.write_bytes(json_dumps(response))

        return response

    async def request(
        self,
        method: str,
        url: str,
        weight: int = 1,
        **kwargs: Any,
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
