import asyncio
import time
from collections.abc import AsyncIterator
from collections.abc import Callable
from contextlib import asynccontextmanager
from email.utils import formatdate
from http import HTTPStatus
from unittest.mock import ANY
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import aiohttp
import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer
from multidict import CIMultiDict
from multidict import CIMultiDictProxy
from yarl import URL

from dipdup.config import HttpConfig
from dipdup.config.http import HttpDatasourceConfig
from dipdup.datasources.http import HttpDatasource


async def test_merge_request_url() -> None:
    base_url = 'https://example.com/api/v1'

    config = HttpDatasourceConfig(url=base_url, http=HttpConfig(replay=False))
    config._name = 'test'
    datasource = HttpDatasource(config)

    async with datasource:
        request_mock = MagicMock()
        request_mock.return_value.__aenter__.return_value._body = 'test'
        datasource._http._session.request = request_mock  # type: ignore[method-assign]

        res = await datasource.get('/endpoint')
        assert res == 'test'

        request_mock.assert_called_once_with(
            method='GET',
            url='api/v1/endpoint',
            headers=ANY,
            raise_for_status=True,
            params=ANY,
        )


def _response_error(status: int) -> aiohttp.ClientResponseError:
    request_info = aiohttp.RequestInfo(
        URL('https://example.com'),
        'GET',
        CIMultiDictProxy(CIMultiDict()),
        URL('https://example.com'),
    )
    return aiohttp.ClientResponseError(
        request_info,
        (),
        status=status,
        headers=CIMultiDictProxy(CIMultiDict()),
    )


@pytest.mark.parametrize(
    ('status', 'expect_ratelimit'),
    [
        (HTTPStatus.TOO_MANY_REQUESTS, True),
        (HTTPStatus.SERVICE_UNAVAILABLE, True),
        (HTTPStatus.BAD_GATEWAY, False),
        (HTTPStatus.INTERNAL_SERVER_ERROR, False),
    ],
)
async def test_retry_treats_503_as_ratelimit(status: int, expect_ratelimit: bool) -> None:
    config = HttpDatasourceConfig(
        url='https://example.com',
        http=HttpConfig(
            replay=False,
            retry_count=1,
            retry_sleep=10.0,
            retry_multiplier=2.0,
            ratelimit_sleep=5.0,
        ),
    )
    config._name = 'test'
    datasource = HttpDatasource(config)
    gateway = datasource._http

    sleeps: list[float] = []

    async def _fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    gateway._request = AsyncMock(side_effect=_response_error(status))  # type: ignore[method-assign]

    with patch('dipdup.http.asyncio.sleep', _fake_sleep):
        with pytest.raises(aiohttp.ClientResponseError):
            await gateway._retry_request('get', '/endpoint')

    # NOTE: retry_count=1 means exactly one sleep before the final (failing) attempt
    assert len(sleeps) == 1
    if expect_ratelimit:
        # NOTE: ratelimit_sleep (5.0) randomized by ±10%, never the retry_sleep (10.0)
        assert 4.5 <= sleeps[0] <= 5.5
    else:
        # NOTE: non-ratelimit errors use the plain retry_sleep
        assert sleeps[0] == 10.0


@pytest.mark.parametrize(
    ('status', 'expect_retry'),
    [
        (HTTPStatus.BAD_REQUEST, False),
        (HTTPStatus.UNAUTHORIZED, False),
        (HTTPStatus.FORBIDDEN, False),
        (HTTPStatus.NOT_FOUND, False),
        (HTTPStatus.UNPROCESSABLE_ENTITY, False),
        (HTTPStatus.REQUEST_TIMEOUT, True),
        (HTTPStatus.TOO_MANY_REQUESTS, True),
        (HTTPStatus.INTERNAL_SERVER_ERROR, True),
        (HTTPStatus.BAD_GATEWAY, True),
        (HTTPStatus.SERVICE_UNAVAILABLE, True),
        (HTTPStatus.GATEWAY_TIMEOUT, True),
    ],
)
async def test_retry_skips_client_errors(status: int, expect_retry: bool) -> None:
    config = HttpDatasourceConfig(
        url='https://example.com',
        http=HttpConfig(
            replay=False,
            retry_count=2,
            retry_sleep=1.0,
            ratelimit_sleep=1.0,
        ),
    )
    config._name = 'test'
    datasource = HttpDatasource(config)
    gateway = datasource._http

    sleeps: list[float] = []

    async def _fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    request_mock = AsyncMock(side_effect=_response_error(status))
    gateway._request = request_mock  # type: ignore[method-assign]

    with patch('dipdup.http.asyncio.sleep', _fake_sleep):
        with pytest.raises(aiohttp.ClientResponseError) as exc_info:
            await gateway._retry_request('get', '/endpoint')

    assert exc_info.value.status == status
    if expect_retry:
        assert request_mock.await_count == 3
        assert len(sleeps) == 2
    else:
        # NOTE: Definitive client errors are raised after a single request
        assert request_mock.await_count == 1
        assert sleeps == []


@asynccontextmanager
async def _serve(*responses: tuple[int, dict[str, str], str]) -> AsyncIterator[tuple[HttpDatasource, list[int]]]:
    """Answer requests with `responses` in order (the last one repeats); yield a datasource pointed at the server"""
    hits: list[int] = []

    async def _handler(request: web.Request) -> web.Response:
        status, headers, text = responses[min(len(hits), len(responses) - 1)]
        hits.append(status)
        return web.Response(status=status, headers=headers, text=text)

    app = web.Application()
    app.router.add_get('/endpoint', _handler)
    async with TestServer(app) as server:
        config = HttpDatasourceConfig(
            url=str(server.make_url('')),
            http=HttpConfig(replay=False, retry_count=10, retry_sleep=0.1, ratelimit_sleep=0.1),
        )
        config._name = 'test'
        datasource = HttpDatasource(config)
        async with datasource:
            yield datasource, hits


@pytest.mark.parametrize(
    'retry_after',
    [
        pytest.param(lambda: '900', id='seconds'),
        pytest.param(lambda: formatdate(time.time() + 900, usegmt=True), id='http-date'),
    ],
)
async def test_retry_after_beyond_cap_fails_fast(retry_after: Callable[[], str]) -> None:
    too_many = (HTTPStatus.TOO_MANY_REQUESTS, {'Retry-After': retry_after()}, 'slow down')
    async with _serve(too_many) as (datasource, hits):
        async with asyncio.timeout(10):
            with pytest.raises(aiohttp.ClientResponseError) as exc_info:
                await datasource.get('/endpoint')

    assert exc_info.value.status == HTTPStatus.TOO_MANY_REQUESTS
    # NOTE: The server asked for 15 minutes; waiting for it would only burn retries
    assert hits == [HTTPStatus.TOO_MANY_REQUESTS]


@pytest.mark.parametrize(
    ('retry_after', 'min_elapsed'),
    [
        pytest.param(lambda: '1', 0.9, id='seconds'),
        # NOTE: HTTP-date has whole-second precision, so +3s means a 2-3s wait
        pytest.param(lambda: formatdate(time.time() + 3, usegmt=True), 1.8, id='http-date'),
    ],
)
async def test_retry_after_within_cap_is_honored(retry_after: Callable[[], str], min_elapsed: float) -> None:
    too_many = (HTTPStatus.TOO_MANY_REQUESTS, {'Retry-After': retry_after()}, 'slow down')
    ok = (HTTPStatus.OK, {'Content-Type': 'application/json'}, '{"ok": true}')
    async with _serve(too_many, ok) as (datasource, hits):
        started_at = time.monotonic()
        async with asyncio.timeout(10):
            res = await datasource.get('/endpoint')
        elapsed = time.monotonic() - started_at

    assert res == {'ok': True}
    assert hits == [HTTPStatus.TOO_MANY_REQUESTS, HTTPStatus.OK]
    # NOTE: Retry-After overrides ratelimit_sleep (0.1), randomized by ±10%
    assert elapsed >= min_elapsed


@pytest.mark.parametrize(
    'retry_after',
    [
        pytest.param(lambda: formatdate(time.time() - 60, usegmt=True), id='past-http-date'),
        pytest.param(lambda: 'soon', id='garbage'),
    ],
)
async def test_retry_after_falls_back_to_ratelimit_sleep(retry_after: Callable[[], str]) -> None:
    too_many = (HTTPStatus.TOO_MANY_REQUESTS, {'Retry-After': retry_after()}, 'slow down')
    ok = (HTTPStatus.OK, {'Content-Type': 'application/json'}, '{"ok": true}')
    async with _serve(too_many, ok) as (datasource, hits):
        started_at = time.monotonic()
        async with asyncio.timeout(10):
            res = await datasource.get('/endpoint')
        elapsed = time.monotonic() - started_at

    assert res == {'ok': True}
    assert hits == [HTTPStatus.TOO_MANY_REQUESTS, HTTPStatus.OK]
    # NOTE: ratelimit_sleep is 0.1
    assert elapsed < 0.5
