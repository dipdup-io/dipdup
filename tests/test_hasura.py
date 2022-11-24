import asyncio
from contextlib import AsyncExitStack
from pathlib import Path

from docker.client import DockerClient  # type: ignore[import]

from dipdup.config import DipDupConfig
from dipdup.config import HasuraConfig
from dipdup.config import PostgresDatabaseConfig
from dipdup.dipdup import DipDup
from dipdup.enums import ReindexingAction
from dipdup.enums import ReindexingReason
from dipdup.hasura import HasuraGateway
from dipdup.project import BaseProject

project_defaults = BaseProject().get_defaults()
docker = DockerClient.from_env()


async def run_postgres_container() -> PostgresDatabaseConfig:
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

    return HasuraConfig(
        url=f'http://{hasura_ip}:8080',
        source='new_source',
        create_source=True,
    )


async def test_configure_hasura() -> None:
    config_path = Path(__file__).parent / 'configs' / 'hic_et_nunc.yml'

    config = DipDupConfig.load([config_path])
    config.database = await run_postgres_container()
    config.hasura = await run_hasura_container(config.database.host)
    config.advanced.reindex[ReindexingReason.schema_modified] = ReindexingAction.ignore
    config.initialize(skip_imports=True)

    async with AsyncExitStack() as stack:
        dipdup = await DipDup.create_dummy(config, stack)
        hasura_gateway = await dipdup._set_up_hasura(stack)
        assert isinstance(hasura_gateway, HasuraGateway)

        await hasura_gateway.configure(force=True)

        config.hasura.camel_case = True
        await hasura_gateway.configure(force=True)
