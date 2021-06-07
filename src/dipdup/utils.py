import asyncio
import logging
import os
import re
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator, NoReturn, Optional

import aiohttp
from tortoise import Tortoise
from tortoise.backends.asyncpg.client import AsyncpgDBClient
from tortoise.transactions import in_transaction

from dipdup import __version__

_logger = logging.getLogger(__name__)


def snake_to_pascal(value: str) -> str:
    """method_name -> MethodName"""
    return ''.join(map(lambda x: x[0].upper() + x[1:], value.replace('.', '_').split('_')))


def pascal_to_snake(name: str) -> str:
    """MethodName -> method_name"""
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name.replace('.', '_'))
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()


@asynccontextmanager
async def tortoise_wrapper(url: str, models: Optional[str] = None) -> AsyncIterator:
    try:
        modules = {'int_models': ['dipdup.models']}
        if models:
            modules['models'] = [models]
        for _ in range(60):
            try:
                await Tortoise.init(
                    db_url=url,
                    modules=modules,  # type: ignore
                )
            except ConnectionRefusedError:
                await asyncio.sleep(1)
            else:
                break
        yield
    finally:
        await Tortoise.close_connections()


async def http_request(method: str, **kwargs):
    """Wrapped aiohttp call with preconfigured headers and logging"""
    async with aiohttp.ClientSession() as session:
        headers = {
            **kwargs.pop('headers', {}),
            'User-Agent': f'dipdup/{__version__}',
        }
        async with getattr(session, method)(
            skip_auto_headers={'User-Agent'},
            headers=headers,
            **kwargs,
        ) as response:
            request_string = kwargs['url'] + '?' + '&'.join([f'{key}={value}' for key, value in kwargs.get('params', {}).items()])
            _logger.debug('Calling `%s`', request_string)
            return await response.json()


async def restart() -> None:
    """Restart preserving CLI arguments"""
    # NOTE: Remove --reindex from arguments to avoid reindexing loop
    argv = sys.argv[:-1] if sys.argv[-1] == '--reindex' else sys.argv
    os.execl(sys.executable, sys.executable, *argv)


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
