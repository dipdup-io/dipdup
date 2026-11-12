from contextlib import AsyncExitStack

import pytest
from pydantic import ValidationError

from dipdup.config import DipDupConfig
from dipdup.config import PostgresDatabaseConfig
from dipdup.config import SqliteDatabaseConfig
from dipdup.database import execute_query
from dipdup.database import get_connection
from dipdup.database import get_tortoise_config
from dipdup.test import create_dummy_dipdup
from dipdup.test import run_in_tmp
from dipdup.test import run_postgres_container
from dipdup.test import tmp_project
from tests import TEST_CONFIGS


def test_server_settings_in_tortoise_config() -> None:
    database_config = PostgresDatabaseConfig(
        host='localhost',
        schema_name='indexer',
        server_settings={
            'synchronous_commit': 'off',
            'statement_timeout': 0,
            'jit': False,
            'enable_seqscan': True,
            'random_page_cost': 1.5,
        },
    )

    tortoise_config = get_tortoise_config(
        database_config.connection_string,
        server_settings=database_config.server_settings,
    )

    credentials = tortoise_config['connections']['default']['credentials']
    assert credentials['server_settings'] == {
        'synchronous_commit': 'off',
        'statement_timeout': '0',
        'jit': 'off',
        'enable_seqscan': 'on',
        'random_page_cost': '1.5',
    }
    assert credentials['schema'] == 'indexer'


def test_connection_string_password_roundtrip() -> None:
    password = 'p a+ss/%&#:@'
    database_config = PostgresDatabaseConfig(host='localhost', password=password)

    tortoise_config = get_tortoise_config(database_config.connection_string)

    assert tortoise_config['connections']['default']['credentials']['password'] == password


def test_server_settings_default_empty() -> None:
    for database_config in (PostgresDatabaseConfig(host='localhost'), SqliteDatabaseConfig()):
        assert database_config.server_settings == {}
        tortoise_config = get_tortoise_config(
            database_config.connection_string,
            server_settings=database_config.server_settings,
        )
        assert 'server_settings' not in tortoise_config['connections']['default']['credentials']


@pytest.mark.parametrize(
    ('key', 'reason'),
    [
        ('search_path', 'DipDup sets it from `schema_name`'),
        ('SEARCH_PATH', 'DipDup sets it from `schema_name`'),
        ('client_encoding', 'asyncpg requires UTF8'),
        ('Client_Encoding', 'asyncpg requires UTF8'),
    ],
)
def test_server_settings_forbidden(key: str, reason: str) -> None:
    with pytest.raises(ValidationError, match=f"`server_settings.{key}` can't be set: {reason}"):
        PostgresDatabaseConfig(host='localhost', server_settings={key: 'other'})


async def test_server_settings_dipdup() -> None:
    container_config = (await run_postgres_container()).config
    config = DipDupConfig(
        spec_version='3.0',
        package='demo_tezos_nft_marketplace',
        database=PostgresDatabaseConfig(
            host=container_config.host,
            port=container_config.port,
            user=container_config.user,
            password=container_config.password,
            database=container_config.database,
            schema_name='indexer',
            server_settings={'synchronous_commit': 'off', 'statement_timeout': 0, 'jit': False},
        ),
    )

    async with AsyncExitStack() as stack:
        await create_dummy_dipdup(config, stack)
        conn = get_connection()
        # NOTE: Repeat to check the settings outlive the reset that asyncpg runs when a connection returns to the pool
        for _ in range(2):
            for name, value in (
                ('synchronous_commit', 'off'),
                ('statement_timeout', '0'),
                ('jit', 'off'),
                ('search_path', 'indexer'),
            ):
                _, rows = await conn.execute_query(f'SHOW {name}')
                assert rows[0][name] == value


async def test_execute_query_returns_rows_postgres() -> None:
    config = DipDupConfig(
        spec_version='3.0',
        package='demo_tezos_nft_marketplace',
        database=(await run_postgres_container()).config,
    )

    async with AsyncExitStack() as stack:
        await create_dummy_dipdup(config, stack)
        await get_connection().execute_script('CREATE TABLE raw_sql (id INT PRIMARY KEY, value TEXT)')

        count, rows = await execute_query(
            sql="INSERT INTO raw_sql VALUES ($1, 'a'), ($2, 'b') RETURNING id", args=(1, 2)
        )
        assert (count, [tuple(row) for row in rows]) == (2, [(1,), (2,)])

        count, rows = await execute_query(sql="update raw_sql set value = 'c' where id = 1 returning id, value")
        assert (count, [tuple(row) for row in rows]) == (1, [(1, 'c')])

        count, rows = await execute_query(sql="UPDATE raw_sql SET value = 'd'")
        assert (count, rows) == (2, [])


async def test_server_settings_cli() -> None:
    package = 'demo_tezos_domains'
    config_paths = [TEST_CONFIGS / f'{package}.yaml', TEST_CONFIGS / 'common_postgres_read_only.yaml']

    async with AsyncExitStack() as stack:
        database_config = (await run_postgres_container()).config
        tmp_package_path, env = await stack.enter_async_context(
            tmp_project(
                config_paths,
                package,
                exists=True,
                env={'POSTGRES_HOST': database_config.host, 'POSTGRES_PORT': str(database_config.port)},
            ),
        )
        await run_in_tmp(tmp_package_path, env, 'schema', 'init')

        read_only_env = {**env, 'READ_ONLY': 'on'}
        for command in (('schema', 'approve'), ('schema', 'wipe', '--force')):
            with pytest.raises(Exception, match='read-only transaction'):
                await run_in_tmp(tmp_package_path, read_only_env, *command)

        await run_in_tmp(tmp_package_path, env, 'schema', 'approve')
