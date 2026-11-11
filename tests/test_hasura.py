from contextlib import AsyncExitStack
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

import orjson as json
import pytest
from aiohttp import ClientResponseError
from aiohttp import web
from aiohttp.pytest_plugin import AiohttpClient
from tortoise import Tortoise

from dipdup.config import DipDupConfig
from dipdup.config import HasuraConfig
from dipdup.config import HttpConfig
from dipdup.config import PostgresDatabaseConfig
from dipdup.config import ReindexingAction
from dipdup.config import ReindexingReason
from dipdup.database import tortoise_wrapper
from dipdup.exceptions import HasuraError
from dipdup.exceptions import UnsupportedAPIError
from dipdup.hasura import HasuraGateway
from dipdup.test import create_dummy_dipdup
from dipdup.test import run_hasura_container
from dipdup.test import run_postgres_container

if TYPE_CHECKING:
    from aiohttp.test_utils import TestClient


async def test_configure_hasura() -> None:
    config_path = Path(__file__).parent / 'configs' / 'demo_tezos_nft_marketplace.yaml'

    config = DipDupConfig.load([config_path])
    postgres = await run_postgres_container()
    # NOTE: The host (this test process) reaches Postgres via 127.0.0.1:<published>.
    config.database = postgres.config
    config.hasura = await run_hasura_container(postgres.internal_host)
    config.advanced.reindex[ReindexingReason.schema_modified] = ReindexingAction.ignore
    config.initialize()

    async with AsyncExitStack() as stack:
        dipdup = await create_dummy_dipdup(config, stack)

        # NOTE: Hasura connects to Postgres from inside its own container, where 127.0.0.1 points at
        # NOTE: Hasura itself — so its source must use the container bridge IP. The host keeps its
        # NOTE: already-open connection (via the published port), and Hasura reaches Postgres
        # NOTE: container-to-container. Both paths hold on Linux, Docker Desktop and WSL alike, so this
        # NOTE: test no longer needs an OS-based skip.
        config.database = PostgresDatabaseConfig(
            kind='postgres',
            host=postgres.internal_host,
            port=5432,
            user='test',
            database='test',
            password='test',
        )

        hasura_gateway = await dipdup._set_up_hasura(stack)
        assert isinstance(hasura_gateway, HasuraGateway)

        await hasura_gateway.configure(force=True)

        config.hasura.camel_case = True
        await hasura_gateway.configure(force=True)


@pytest.mark.parametrize('hasura_version', ['v1.0.0', 'v2.15.0'])
async def test_unsupported_versions(hasura_version: str, aiohttp_client: AiohttpClient) -> None:
    async def healthcheck_response(request: web.Request) -> web.Response:
        return web.Response(
            content_type='application/json',
        )

    async def version_response(request: web.Request) -> web.Response:
        return web.Response(
            body=json.dumps({'version': hasura_version}),
            content_type='application/json',
        )

    fake_api = web.Application()
    fake_api.router.add_get('/healthz', healthcheck_response)
    fake_api.router.add_get('/v1/version', version_response)
    fake_client: TestClient[Any, Any] = await aiohttp_client(fake_api)

    fake_client_url = f'http://{fake_client.server.host}:{fake_client.server.port}'
    hasura_config = HasuraConfig(url=fake_client_url)
    postgres_config = PostgresDatabaseConfig(kind='postgres', host='localhost')

    hasura_gateway = HasuraGateway('demo_tezos_nft_marketplace', hasura_config, postgres_config)

    with pytest.raises(UnsupportedAPIError):
        async with hasura_gateway:
            async with tortoise_wrapper('sqlite://:memory:', 'demo_tezos_nft_marketplace.models'):
                await Tortoise.generate_schemas()
                await hasura_gateway.configure()


async def _healthcheck(statuses: list[int], hits: list[int], aiohttp_client: AiohttpClient) -> None:
    """Run the startup healthcheck against a server answering `statuses` in order, then 200; record served statuses in `hits`"""

    async def version_response(request: web.Request) -> web.Response:
        status = statuses[len(hits)] if len(hits) < len(statuses) else 200
        hits.append(status)
        if status != 200:
            return web.Response(status=status, text='404 page not found')
        return web.json_response({'version': 'v2.40.0'})

    fake_api = web.Application()
    fake_api.router.add_get('/v1/version', version_response)
    fake_client: TestClient[Any, Any] = await aiohttp_client(fake_api)

    hasura_gateway = HasuraGateway(
        'demo_tezos_nft_marketplace',
        HasuraConfig(url=f'http://{fake_client.server.host}:{fake_client.server.port}'),
        PostgresDatabaseConfig(kind='postgres', host='localhost'),
        HttpConfig(retry_sleep=0.01, retry_multiplier=1.0),
    )
    async with hasura_gateway:
        await hasura_gateway._healthcheck()


async def test_healthcheck_waits_for_hasura(aiohttp_client: AiohttpClient) -> None:
    # NOTE: A reverse proxy answers 404 until Hasura behind it is up
    hits: list[int] = []
    await _healthcheck([404, 404, 502, 503, 404], hits, aiohttp_client)
    assert hits == [404, 404, 502, 503, 404, 200]


async def test_healthcheck_gives_up_on_404(aiohttp_client: AiohttpClient) -> None:
    hits: list[int] = []
    with pytest.raises(HasuraError) as exc_info:
        await _healthcheck([404] * 100, hits, aiohttp_client)
    assert isinstance(exc_info.value.__cause__, ClientResponseError)
    assert exc_info.value.__cause__.status == 404
    assert hits == [404] * 21


@pytest.mark.parametrize('status', [401, 403])
async def test_healthcheck_fails_fast_on_auth_error(status: int, aiohttp_client: AiohttpClient) -> None:
    hits: list[int] = []
    with pytest.raises(HasuraError):
        await _healthcheck([status] * 100, hits, aiohttp_client)
    assert hits == [status]
