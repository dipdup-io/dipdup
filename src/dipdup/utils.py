import asyncio
import logging
import os
import re
import sys
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

import aiohttp
from tortoise import Tortoise
from tortoise.backends.asyncpg.client import AsyncpgDBClient
from tortoise.transactions import in_transaction

from dipdup import __version__

_logger = logging.getLogger(__name__)


@asynccontextmanager
async def slowdown(seconds: int):
    """Sleep if nested block executed faster than X seconds"""
    started_at = time.time()
    yield
    finished_at = time.time()
    time_spent = finished_at - started_at
    if time_spent < seconds:
        await asyncio.sleep(seconds - time_spent)


def snake_to_pascal(value: str) -> str:
    """method_name -> MethodName"""
    return ''.join(map(lambda x: x[0].upper() + x[1:], value.replace('.', '_').split('_')))


def pascal_to_snake(name: str) -> str:
    """MethodName -> method_name"""
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name.replace('.', '_'))
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()


@asynccontextmanager
async def tortoise_wrapper(url: str, models: Optional[str] = None) -> AsyncIterator:
    """Initialize Tortoise with internal and project models, close connections when done"""
    attempts = 60
    try:
        modules = {'int_models': ['dipdup.models']}
        if models:
            modules['models'] = [models]
        for attempt in range(attempts):
            try:
                await Tortoise.init(
                    db_url=url,
                    modules=modules,  # type: ignore
                )
            except ConnectionRefusedError:
                _logger.warning('Can\'t establish database connection, attempt %s/%s', attempt, attempts)
                if attempt == attempts - 1:
                    raise
                await asyncio.sleep(1)
            else:
                break
        yield
    finally:
        await Tortoise.close_connections()


@asynccontextmanager
async def in_global_transaction():
    """Enforce using transaction for all queries inside wrapped block. Works for a single DB only."""
    if list(Tortoise._connections.keys()) != ['default']:
        raise RuntimeError('`in_global_transaction` wrapper works only with a single DB connection')
    async with in_transaction() as conn:
        # NOTE: SQLite hacks
        conn.filename = ''
        conn.pragmas = {}

        original_conn = Tortoise._connections['default']
        Tortoise._connections['default'] = conn
        yield
    Tortoise._connections['default'] = original_conn


async def http_request(session: aiohttp.ClientSession, method: str, **kwargs):
    """Wrapped aiohttp call with preconfigured headers and logging"""
    headers = {
        **kwargs.pop('headers', {}),
        'User-Agent': f'dipdup/{__version__}',
    }
    request_string = kwargs['url'] + '?' + '&'.join([f'{key}={value}' for key, value in kwargs.get('params', {}).items()])
    _logger.debug('Calling `%s`', request_string)
    async with getattr(session, method)(
        skip_auto_headers={'User-Agent'},
        headers=headers,
        **kwargs,
    ) as response:
        return await response.json()


async def restart() -> None:
    """Restart preserving CLI arguments"""
    # NOTE: Remove --reindex from arguments to avoid reindexing loop
    if '--reindex' in sys.argv:
        sys.argv.remove('--reindex')
    os.execl(sys.executable, sys.executable, *sys.argv)


async def reindex() -> None:
    """Drop all tables or whole database and restart with the same CLI arguments"""
    if isinstance(Tortoise._connections['default'], AsyncpgDBClient):
        async with in_transaction() as conn:
            await conn.execute_script(
                '''
                DO $$ DECLARE
                    r RECORD;
                BEGIN
                    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = current_schema()) LOOP
                        EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                    END LOOP;
                END $$;
                '''
            )
    else:
        await Tortoise._drop_databases()
    # NOTE: Tortoise can't recover after dropping database for some reason, restart.
    await restart()
