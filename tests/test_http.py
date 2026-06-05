from http import HTTPStatus
from unittest.mock import ANY
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import aiohttp
import pytest
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
