import pytest
from pydantic import ValidationError

from dipdup.config import PostgresDatabaseConfig
from dipdup.config import SqliteDatabaseConfig
from dipdup.database import get_connection
from dipdup.database import get_tortoise_config
from dipdup.database import tortoise_wrapper
from dipdup.test import run_postgres_container


def test_server_settings_in_tortoise_config() -> None:
    database_config = PostgresDatabaseConfig(
        host='localhost',
        schema_name='indexer',
        server_settings={'synchronous_commit': 'off', 'work_mem': '64MB'},
    )

    tortoise_config = get_tortoise_config(
        database_config.connection_string,
        server_settings=database_config.server_settings,
    )

    credentials = tortoise_config['connections']['default']['credentials']
    assert credentials['server_settings'] == {'synchronous_commit': 'off', 'work_mem': '64MB'}
    assert credentials['schema'] == 'indexer'


def test_server_settings_default_empty() -> None:
    for database_config in (PostgresDatabaseConfig(host='localhost'), SqliteDatabaseConfig()):
        assert database_config.server_settings == {}
        tortoise_config = get_tortoise_config(
            database_config.connection_string,
            server_settings=database_config.server_settings,
        )
        assert 'server_settings' not in tortoise_config['connections']['default']['credentials']


def test_server_settings_search_path_rejected() -> None:
    with pytest.raises(ValidationError, match='use `schema_name` instead'):
        PostgresDatabaseConfig(host='localhost', server_settings={'search_path': 'other'})


async def test_server_settings_postgres() -> None:
    container_config = (await run_postgres_container()).config
    database_config = PostgresDatabaseConfig(
        host=container_config.host,
        port=container_config.port,
        user=container_config.user,
        password=container_config.password,
        database=container_config.database,
        schema_name='indexer',
        server_settings={'synchronous_commit': 'off', 'work_mem': '64MB'},
    )

    async with tortoise_wrapper(
        database_config.connection_string,
        server_settings=database_config.server_settings,
    ):
        conn = get_connection()
        await conn.execute_script('CREATE SCHEMA IF NOT EXISTS indexer')
        # NOTE: Repeat to check the settings outlive the reset that asyncpg runs when a connection returns to the pool
        for _ in range(2):
            _, rows = await conn.execute_query('SHOW synchronous_commit')
            assert rows[0]['synchronous_commit'] == 'off'
            _, rows = await conn.execute_query('SHOW work_mem')
            assert rows[0]['work_mem'] == '64MB'
            _, rows = await conn.execute_query('SHOW search_path')
            assert rows[0]['search_path'] == 'indexer'
