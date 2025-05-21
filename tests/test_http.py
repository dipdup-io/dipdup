from unittest.mock import ANY
from unittest.mock import MagicMock

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
