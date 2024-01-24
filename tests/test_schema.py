from contextlib import AbstractAsyncContextManager
from contextlib import AsyncExitStack

from dipdup.database import get_connection
from dipdup.database import get_tables
from dipdup.database import tortoise_wrapper
from dipdup.test import run_in_tmp
from dipdup.test import run_postgres_container
from dipdup.test import tmp_project
from tests import TEST_CONFIGS

_dipdup_tables = {
    'dipdup_contract_metadata',
    'dipdup_model_update',
    'dipdup_schema',
    'dipdup_contract',
    'dipdup_token_metadata',
    'dipdup_head',
    'dipdup_index',
    'dipdup_meta',
}


async def test_schema_sqlite() -> None:
    package = 'demo_domains'
    config_path = TEST_CONFIGS / f'{package}.yml'
    env_config_path = TEST_CONFIGS / 'test_sqlite.yaml'

    async with AsyncExitStack() as stack:
        tmp_package_path, env = await stack.enter_async_context(
            tmp_project(
                [config_path, env_config_path],
                package,
                exists=True,
            ),
        )

        def tortoise() -> AbstractAsyncContextManager[None]:
            return tortoise_wrapper(
                f'sqlite://{tmp_package_path}/db.sqlite3',
                f'{package}.models',
            )

        async with tortoise():
            conn = get_connection()
            assert await get_tables() == set()

        await run_in_tmp(tmp_package_path, env, 'schema', 'init')

        async with tortoise():
            conn = get_connection()
            assert await get_tables() == _dipdup_tables | {'tld', 'record', 'domain', 'expiry', 'sqlite_sequence'}
            await conn.execute_script('CREATE TABLE test (id INTEGER PRIMARY KEY);')
            assert await get_tables() == _dipdup_tables | {
                'tld',
                'record',
                'domain',
                'expiry',
                'sqlite_sequence',
                'test',
            }

        await run_in_tmp(tmp_package_path, env, 'schema', 'wipe', '--force')

        async with tortoise():
            conn = get_connection()
            assert await get_tables() == set()


async def test_schema_sqlite_immune() -> None:
    package = 'demo_domains'
    config_path = TEST_CONFIGS / f'{package}.yml'
    env_config_path = TEST_CONFIGS / 'test_sqlite_immune.yaml'

    async with AsyncExitStack() as stack:
        tmp_package_path, env = await stack.enter_async_context(
            tmp_project(
                [config_path, env_config_path],
                package,
                exists=True,
            ),
        )

        def tortoise() -> AbstractAsyncContextManager[None]:
            return tortoise_wrapper(
                f'sqlite://{tmp_package_path}/db.sqlite3',
                f'{package}.models',
            )

        async with tortoise():
            conn = get_connection()
            assert await get_tables() == set()

        await run_in_tmp(tmp_package_path, env, 'schema', 'init')

        async with tortoise():
            conn = get_connection()
            assert await get_tables() == _dipdup_tables | {'tld', 'record', 'domain', 'expiry', 'sqlite_sequence'}
            await conn.execute_script('CREATE TABLE test (id INTEGER PRIMARY KEY);')
            assert await get_tables() == _dipdup_tables | {
                'tld',
                'record',
                'domain',
                'expiry',
                'sqlite_sequence',
                'test',
            }

        await run_in_tmp(tmp_package_path, env, 'schema', 'wipe', '--force')

        async with tortoise():
            conn = get_connection()
            assert await get_tables() == {'dipdup_meta', 'test', 'domain', 'tld'}


async def test_schema_postgres() -> None:
    package = 'demo_domains'
    config_path = TEST_CONFIGS / f'{package}.yml'
    env_config_path = TEST_CONFIGS / 'test_postgres.yaml'

    async with AsyncExitStack() as stack:
        tmp_package_path, env = await stack.enter_async_context(
            tmp_project(
                [config_path, env_config_path],
                package,
                exists=True,
            ),
        )

        database_config = await run_postgres_container()
        env['POSTGRES_HOST'] = database_config.host

        def tortoise() -> AbstractAsyncContextManager[None]:
            return tortoise_wrapper(
                database_config.connection_string,
                f'{package}.models',
            )

        async with tortoise():
            conn = get_connection()
            assert await get_tables() == set()

        await run_in_tmp(tmp_package_path, env, 'schema', 'init')

        async with tortoise():
            conn = get_connection()
            assert await get_tables() == _dipdup_tables | {'tld', 'record', 'domain', 'expiry'}
            await conn.execute_script('CREATE TABLE test (id INTEGER PRIMARY KEY);')
            assert await get_tables() == _dipdup_tables | {'tld', 'record', 'domain', 'expiry', 'test'}

        await run_in_tmp(tmp_package_path, env, 'schema', 'wipe', '--force')

        async with tortoise():
            conn = get_connection()
            assert await get_tables() == {'dipdup_meta'}


async def test_schema_postgres_immune() -> None:
    package = 'demo_domains'
    config_path = TEST_CONFIGS / f'{package}.yml'
    env_config_path = TEST_CONFIGS / 'test_postgres_immune.yaml'

    async with AsyncExitStack() as stack:
        tmp_package_path, env = await stack.enter_async_context(
            tmp_project(
                [config_path, env_config_path],
                package,
                exists=True,
            ),
        )

        database_config = await run_postgres_container()
        env['POSTGRES_HOST'] = database_config.host

        def tortoise() -> AbstractAsyncContextManager[None]:
            return tortoise_wrapper(
                database_config.connection_string,
                f'{package}.models',
            )

        async with tortoise():
            conn = get_connection()
            assert await get_tables() == set()

        await run_in_tmp(tmp_package_path, env, 'schema', 'init')

        async with tortoise():
            conn = get_connection()
            assert await get_tables() == _dipdup_tables | {'tld', 'record', 'domain', 'expiry'}
            await conn.execute_script('CREATE TABLE test (id INTEGER PRIMARY KEY);')
            assert await get_tables() == _dipdup_tables | {'tld', 'record', 'domain', 'expiry', 'test'}

        await run_in_tmp(tmp_package_path, env, 'schema', 'wipe', '--force')

        async with tortoise():
            conn = get_connection()
            assert await get_tables() == {'dipdup_meta', 'test', 'domain', 'tld'}
