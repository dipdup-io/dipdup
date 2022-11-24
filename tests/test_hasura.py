from contextlib import AsyncExitStack
from pathlib import Path

import orjson as json
import pytest
from aiohttp import web
from docker.client import DockerClient  # type: ignore[import]
from tortoise import Tortoise

from dipdup.config import DipDupConfig
from dipdup.config import HasuraConfig
from dipdup.config import PostgresDatabaseConfig
from dipdup.dipdup import DipDup
from dipdup.exceptions import HasuraError
from dipdup.exceptions import UnsupportedAPIError
from dipdup.hasura import HasuraGateway
from dipdup.project import BaseProject
from dipdup.utils.database import tortoise_wrapper


@pytest.mark.skip('FIXME: syntax error at or near ","')
async def test_configure_hasura() -> None:
    project_defaults = BaseProject().get_defaults()
    config_path = Path(__file__).parent / 'configs' / 'hic_et_nunc.yml'

    config = DipDupConfig.load([config_path])
    config.initialize(skip_imports=True)

    docker = DockerClient.from_env()
    postgres_container = docker.containers.run(
        image=project_defaults['postgresql_image'],
        environment={
            'POSTGRES_USER': 'test',
            'POSTGRES_PASSWORD': 'test',
            'POSTGRES_DB': 'test',
        },
        detach=True,
        remove=True,
    )
    postgres_container.reload()
    postgres_ip = postgres_container.attrs['NetworkSettings']['IPAddress']

    config.database = PostgresDatabaseConfig(
        kind='postgres',
        host=postgres_ip,
        port=5432,
        user='test',
        database='test',
        password='test',
    )
    config.initialize()
    dipdup = DipDup(config)

    async with AsyncExitStack() as stack:
        await stack.enter_async_context(
            tortoise_wrapper(
                config.database.connection_string,
                'demo_hic_et_nunc.models',
            )
        )
        await dipdup._set_up_database(stack)
        await dipdup._set_up_hooks(set())
        await dipdup._initialize_schema()

        hasura_container = docker.containers.run(
            image=project_defaults['hasura_image'],
            environment={
                'HASURA_GRAPHQL_DATABASE_URL': f'postgres://test:test@{postgres_ip}:5432',
            },
            detach=True,
            remove=True,
        )
        hasura_container.reload()
        hasura_ip = hasura_container.attrs['NetworkSettings']['IPAddress']

        config.hasura = HasuraConfig(
            url=f'http://{hasura_ip}:8080',
            source='new_source',
            create_source=True,
        )
        hasura_gateway = HasuraGateway('demo_hic_et_nunc', config.hasura, config.database)
        await stack.enter_async_context(hasura_gateway)

        try:
            await hasura_gateway.configure(force=True)

            config.hasura.camel_case = True

            await hasura_gateway.configure(force=True)
        except HasuraError:
            dipdup._ctx.logger.info(hasura_container.logs())
            raise


@pytest.mark.parametrize('hasura_version', ['v1.0.0', 'v2.15.0'])
async def test_unsupported_versions(hasura_version: str, aiohttp_client) -> None:
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
    fake_client = await aiohttp_client(fake_api)

    hasura_config = HasuraConfig('http://localhost')
    postgres_config = PostgresDatabaseConfig('postgres', 'localhost')

    hasura_gateway = HasuraGateway('demo_hic_et_nunc', hasura_config, postgres_config)
    # NOTE: Some aiohttp pytest plugin trickery I have no time to investigate
    hasura_gateway._http._HTTPGateway__session = fake_client  # type: ignore[attr-defined]

    with pytest.raises(UnsupportedAPIError):
        async with tortoise_wrapper('sqlite://:memory:', 'demo_hic_et_nunc.models'):
            await Tortoise.generate_schemas()
            await hasura_gateway.configure()
