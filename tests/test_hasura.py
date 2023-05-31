import asyncio
import atexit
import os
from contextlib import AsyncExitStack
from pathlib import Path

import orjson as json
import pytest
from aiohttp import web
from aiohttp.pytest_plugin import AiohttpClient
from aiohttp.test_utils import TestClient
from docker.client import DockerClient  # type: ignore[import]
from tortoise import Tortoise

from dipdup.config import DipDupConfig
from dipdup.config import HasuraConfig
from dipdup.config import PostgresDatabaseConfig
from dipdup.database import tortoise_wrapper
from dipdup.dipdup import DipDup
from dipdup.exceptions import UnsupportedAPIError
from dipdup.hasura import HasuraGateway
from dipdup.models import ReindexingAction
from dipdup.models import ReindexingReason
from dipdup.project import DEFAULT_ANSWERS


def get_docker_client() -> DockerClient:
    docker_socks = (
        Path('/var/run/docker.sock'),
        Path.home() / 'Library' / 'Containers' / 'com.docker.docker' / 'Data' / 'vms' / '0' / 'docker.sock',
        Path.home() / 'Library' / 'Containers' / 'com.docker.docker' / 'Data' / 'docker.sock',
    )
    for path in docker_socks:
        if path.exists():
            return DockerClient(base_url=f'unix://{path}')
    else:
        pytest.skip('Docker socket not found', allow_module_level=True)


async def run_postgres_container() -> PostgresDatabaseConfig:
    docker = get_docker_client()
    postgres_container = docker.containers.run(
        image=DEFAULT_ANSWERS['postgresql_image'],
        environment={
            'POSTGRES_USER': 'test',
            'POSTGRES_PASSWORD': 'test',
            'POSTGRES_DB': 'test',
        },
        detach=True,
        remove=True,
    )
    atexit.register(postgres_container.stop)
    postgres_container.reload()
    postgres_ip = postgres_container.attrs['NetworkSettings']['IPAddress']

    while not postgres_container.exec_run('pg_isready').exit_code == 0:
        await asyncio.sleep(0.1)

    return PostgresDatabaseConfig(
        kind='postgres',
        host=postgres_ip,
        port=5432,
        user='test',
        database='test',
        password='test',
    )


async def run_hasura_container(postgres_ip: str) -> HasuraConfig:
    docker = get_docker_client()
    hasura_container = docker.containers.run(
        image=DEFAULT_ANSWERS['hasura_image'],
        environment={
            'HASURA_GRAPHQL_DATABASE_URL': f'postgres://test:test@{postgres_ip}:5432',
        },
        detach=True,
        remove=True,
    )
    atexit.register(hasura_container.stop)
    hasura_container.reload()
    hasura_ip = hasura_container.attrs['NetworkSettings']['IPAddress']

    return HasuraConfig(
        url=f'http://{hasura_ip}:8080',
        source='new_source',
        create_source=True,
    )


async def test_configure_hasura() -> None:
    if os.uname().sysname != 'Linux' or 'microsoft' in os.uname().release:  # check for WSL, Windows, mac and else
        pytest.skip('Test is not supported for os archetecture', allow_module_level=True)

    config_path = Path(__file__).parent / 'configs' / 'demo_nft_marketplace.yml'

    config = DipDupConfig.load([config_path])
    config.database = await run_postgres_container()
    config.hasura = await run_hasura_container(config.database.host)
    config.advanced.reindex[ReindexingReason.schema_modified] = ReindexingAction.ignore
    config.initialize()

    async with AsyncExitStack() as stack:
        dipdup = await DipDup.create_dummy(config, stack)
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
    fake_client: TestClient = await aiohttp_client(fake_api)

    fake_client_url = f'http://{fake_client.server.host}:{fake_client.server.port}'
    hasura_config = HasuraConfig(fake_client_url)
    postgres_config = PostgresDatabaseConfig('postgres', 'localhost')

    hasura_gateway = HasuraGateway('demo_nft_marketplace', hasura_config, postgres_config)

    with pytest.raises(UnsupportedAPIError):
        async with hasura_gateway:
            async with tortoise_wrapper('sqlite://:memory:', 'demo_nft_marketplace.models'):
                await Tortoise.generate_schemas()
                await hasura_gateway.configure()
