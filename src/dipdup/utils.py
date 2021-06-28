import asyncio
import logging
import re
import time
from contextlib import asynccontextmanager
from logging import Logger
from typing import Any, AsyncIterator, Iterator, List, Optional

import aiohttp
from tortoise import Tortoise
from tortoise.backends.asyncpg.client import AsyncpgDBClient
from tortoise.backends.base.client import TransactionContext
from tortoise.backends.sqlite.client import SqliteClient
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


def split_by_chunks(input_: List[Any], size: int) -> Iterator[List[Any]]:
    i = 0
    while i < len(input_):
        yield input_[i : i + size]
        i += size


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
        conn: TransactionContext
        original_conn = Tortoise._connections['default']
        Tortoise._connections['default'] = conn

        if isinstance(original_conn, SqliteClient):
            conn.filename = original_conn.filename
            conn.pragmas = original_conn.pragmas
        elif isinstance(original_conn, AsyncpgDBClient):
            conn._pool = original_conn._pool
            conn._template = original_conn._template
        else:
            raise NotImplementedError(
                '`in_global_transaction` wrapper was not tested with database backends other then aiosqlite and asyncpg'
            )

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


class FormattedLogger(Logger):
    def __init__(
        self,
        name: str,
        fmt: Optional[str] = None,
    ):
        logger = logging.getLogger(name)
        self.__class__ = type(FormattedLogger.__name__, (self.__class__, logger.__class__), {})
        self.__dict__ = logger.__dict__
        self.fmt = fmt

    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False, stacklevel=1):
        if self.fmt:
            msg = self.fmt.format(msg)
        super()._log(level, msg, args, exc_info, extra, stack_info, stacklevel)
