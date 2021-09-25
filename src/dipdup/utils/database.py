import asyncio
import decimal
import hashlib
import importlib
import logging
from contextlib import asynccontextmanager
from os.path import dirname, join
from pathlib import Path
from typing import Any, AsyncIterator, Iterator, Optional, Tuple, Type

from tortoise import Tortoise
from tortoise.backends.asyncpg.client import AsyncpgDBClient
from tortoise.backends.base.client import BaseDBAsyncClient, TransactionContext
from tortoise.backends.sqlite.client import SqliteClient
from tortoise.fields import DecimalField
from tortoise.models import Model
from tortoise.transactions import in_transaction
from tortoise.utils import get_schema_sql

from dipdup.exceptions import DatabaseConfigurationError
from dipdup.utils import pascal_to_snake

_logger = logging.getLogger('dipdup.database')
_truncate_schema_sql = Path(join(dirname(__file__), 'truncate_schema.sql')).read_text()


@asynccontextmanager
async def tortoise_wrapper(url: str, models: Optional[str] = None, timeout: int = 60) -> AsyncIterator:
    """Initialize Tortoise with internal and project models, close connections when done"""
    modules = {'int_models': ['dipdup.models']}
    if models:
        modules['models'] = [models]
    try:
        for attempt in range(timeout):
            try:
                await Tortoise.init(
                    db_url=url,
                    modules=modules,  # type: ignore
                )
            except (OSError, ConnectionRefusedError):
                _logger.warning('Can\'t establish database connection, attempt %s/%s', attempt, timeout)
                if attempt == timeout - 1:
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
            raise NotImplementedError

        yield

    Tortoise._connections['default'] = original_conn


def is_model_class(obj: Any) -> bool:
    """Is subclass of tortoise.Model, but not the base class"""
    return isinstance(obj, type) and issubclass(obj, Model) and obj != Model and not getattr(obj.Meta, 'abstract', False)


def iter_models(package: str) -> Iterator[Tuple[str, Type[Model]]]:
    """Iterate over built-in and project's models"""
    dipdup_models = importlib.import_module('dipdup.models')
    package_models = importlib.import_module(f'{package}.models')

    for models in (dipdup_models, package_models):
        for attr in dir(models):
            model = getattr(models, attr)
            if is_model_class(model):
                app = 'int_models' if models.__name__ == 'dipdup.models' else 'models'
                yield app, model


def set_decimal_context(package: str) -> None:
    """Adjust system decimal context to match database precision"""
    context = decimal.getcontext()
    prec = context.prec
    for _, model in iter_models(package):
        for field in model._meta.fields_map.values():
            if isinstance(field, DecimalField):
                context.prec = max(context.prec, field.max_digits + field.max_digits)
    if prec < context.prec:
        _logger.warning('Decimal context precision has been updated: %s -> %s', prec, context.prec)
        # NOTE: DefaultContext used for new threads
        decimal.DefaultContext.prec = context.prec
        decimal.setcontext(context)


def get_schema_hash(conn: BaseDBAsyncClient) -> str:
    """Get hash of the current schema"""
    schema_sql = get_schema_sql(conn, False)
    # NOTE: Column order could differ in two generated schemas for the same models, drop commas and sort strings to eliminate this
    processed_schema_sql = '\n'.join(sorted(schema_sql.replace(',', '').split('\n'))).encode()
    return hashlib.sha256(processed_schema_sql).hexdigest()


async def set_schema(conn: BaseDBAsyncClient, name: str) -> None:
    """Set schema for the connection"""
    if isinstance(conn, SqliteClient):
        raise NotImplementedError

    await conn.execute_script(f'SET search_path TO {name}')


async def create_schema(conn: BaseDBAsyncClient, name: str) -> None:
    if isinstance(conn, SqliteClient):
        raise NotImplementedError

    await conn.execute_script(f'CREATE SCHEMA IF NOT EXISTS {name}')
    # FIXME: Oh...
    await conn.execute_script(_truncate_schema_sql)


async def generate_schema(conn: BaseDBAsyncClient, name: str) -> None:
    if isinstance(conn, SqliteClient):
        await Tortoise.generate_schemas()
    elif isinstance(conn, AsyncpgDBClient):
        await create_schema(conn, name)
        await set_schema(conn, name)
        await Tortoise.generate_schemas()
    else:
        raise NotImplementedError


async def truncate_schema(conn: BaseDBAsyncClient, name: str) -> None:
    if isinstance(conn, SqliteClient):
        raise NotImplementedError

    await conn.execute_script(_truncate_schema_sql)
    await conn.execute_script(f"SELECT truncate_schema('{name}')")


async def drop_schema(conn: BaseDBAsyncClient, name: str) -> None:
    if isinstance(conn, SqliteClient):
        raise NotImplementedError

    await conn.execute_script(f'DROP SCHEMA IF EXISTS {name}')


async def move_table(conn: BaseDBAsyncClient, name: str, schema: str, new_schema: str) -> None:
    """Move table from one schema to another"""
    if isinstance(conn, SqliteClient):
        raise NotImplementedError

    await conn.execute_script(f'ALTER TABLE {schema}.{name} SET SCHEMA {new_schema}')


def validate_models(package: str) -> None:
    """Validate project models"""
    for _, model in iter_models(package):
        # NOTE: Resolve missing table names before Tortoise does
        if model._meta.db_table is None:
            model._meta.db_table = pascal_to_snake(model.__name__)

        name = model._meta.db_table
        if name != pascal_to_snake(name):
            raise DatabaseConfigurationError('Table names should be in snake_case', model)
        for field in model._meta.fields_map.values():
            if field.model_field_name != pascal_to_snake(field.model_field_name):
                raise DatabaseConfigurationError('Column names should be in snake_case', model)
