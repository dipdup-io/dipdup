import asyncio
from contextlib import AsyncExitStack
from pathlib import Path

import pytest

from dipdup import env
from dipdup.config import DipDupConfig
from dipdup.config import PostgresDatabaseConfig
from dipdup.config import SqliteDatabaseConfig
from dipdup.context import DipDupContext
from dipdup.database import get_connection
from dipdup.exceptions import FrameworkException
from dipdup.test import create_dummy_dipdup
from dipdup.test import run_postgres_container

CONFIG_PATH = Path(__file__).parent / 'configs' / 'demo_tezos_nft_marketplace.yaml'
SCHEMA_NAME = 'hook_sql'
TIMEOUT = 10


@pytest.fixture
def sql_dir(tmp_path: Path) -> Path:
    path = tmp_path / 'sql' / 'probe'
    path.mkdir(parents=True)
    (path / '01_create.sql').write_text('CREATE TABLE probe (id integer);\nINSERT INTO probe VALUES (1);')
    (path / '02_insert.sql').write_text('INSERT INTO probe VALUES (2);')
    return path


async def _create_ctx(
    database: PostgresDatabaseConfig | SqliteDatabaseConfig,
    stack: AsyncExitStack,
    sql_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> DipDupContext:
    config = DipDupConfig.load([CONFIG_PATH])
    config.database = database
    dipdup = await create_dummy_dipdup(config, stack)
    ctx = dipdup._ctx
    # NOTE: `env.TEST` short-circuits `execute_sql_script`; the SQL directory lives outside the package.
    monkeypatch.setattr(env, 'TEST', False)
    monkeypatch.setattr(ctx, '_get_sql_path', lambda name: sql_dir)
    return ctx


async def _probe_ids() -> list[int]:
    _, rows = await get_connection().execute_query(f'SELECT id FROM {SCHEMA_NAME}.probe ORDER BY id')
    return [row['id'] for row in rows]


async def test_dedicated_connection_does_not_wait_for_shared_one(
    sql_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = (await run_postgres_container()).config
    database.schema_name = SCHEMA_NAME

    async with AsyncExitStack() as stack:
        ctx = await _create_ctx(database, stack, sql_dir, monkeypatch)

        # NOTE: Hold the only connection of the shared pool, like a long statement in another task does.
        async with get_connection().acquire_connection():
            async with asyncio.timeout(TIMEOUT):
                await ctx.execute_sql_script('probe', dedicated_connection=True)

        # NOTE: Unqualified `probe` resolved to the config schema, files ran in order.
        assert await _probe_ids() == [1, 2]


async def test_dedicated_connection_refused_inside_transaction(
    sql_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with AsyncExitStack() as stack:
        ctx = await _create_ctx(SqliteDatabaseConfig(kind='sqlite'), stack, sql_dir, monkeypatch)

        async with asyncio.timeout(TIMEOUT):
            with pytest.raises(FrameworkException, match='transaction'):
                async with ctx.transactions.in_transaction():
                    await ctx.execute_sql_script('probe', dedicated_connection=True)


async def test_dedicated_connection_on_sqlite_uses_shared_one(
    sql_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Guard: on SQLite the flag falls back to the shared connection and the script still runs."""
    async with AsyncExitStack() as stack:
        ctx = await _create_ctx(SqliteDatabaseConfig(kind='sqlite'), stack, sql_dir, monkeypatch)

        async with asyncio.timeout(TIMEOUT):
            await ctx.execute_sql_script('probe', dedicated_connection=True)

        _, rows = await get_connection().execute_query('SELECT id FROM probe ORDER BY id')
        assert [row['id'] for row in rows] == [1, 2]
