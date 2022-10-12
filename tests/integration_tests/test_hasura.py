from contextlib import AsyncExitStack
from os import environ as env
from pathlib import Path
from unittest import IsolatedAsyncioTestCase

import pytest
from docker.client import DockerClient  # type: ignore

from dipdup.config import DipDupConfig
from dipdup.config import HasuraConfig
from dipdup.config import PostgresDatabaseConfig
from dipdup.dipdup import DipDup
from dipdup.exceptions import HasuraError
from dipdup.hasura import HasuraGateway
from dipdup.project import BaseProject
from dipdup.utils.database import tortoise_wrapper

if env.get('CI') == 'true' and env.get('RUNNER_OS') != 'Linux':
    pytest.skip('skipping integration tests on CI', allow_module_level=True)


class HasuraTest(IsolatedAsyncioTestCase):
    maxDiff = None

    async def test_configure_hasura(self) -> None:
        project_defaults = BaseProject().get_defaults()
        config_path = Path(__file__).parent / 'hic_et_nunc.yml'

        config = DipDupConfig.load([config_path])
        config.initialize(skip_imports=True)

        async with AsyncExitStack() as stack:
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
            dipdup = DipDup(config)
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
