import asyncio
import atexit
import decimal
import hashlib
import importlib
import logging
from contextlib import asynccontextmanager
from contextlib import suppress
from pathlib import Path
from types import ModuleType
from typing import Any
from typing import AsyncIterator
from typing import Iterable
from typing import Iterator
from typing import cast

import asyncpg.exceptions  # type: ignore[import]
import sqlparse  # type: ignore[import]
from tortoise import Tortoise
from tortoise.backends.asyncpg.client import AsyncpgDBClient
from tortoise.backends.base.client import BaseDBAsyncClient
from tortoise.backends.base.executor import EXECUTOR_CACHE
from tortoise.backends.sqlite.client import SqliteClient
from tortoise.connection import connections
from tortoise.fields import DecimalField
from tortoise.models import Model as TortoiseModel
from tortoise.utils import get_schema_sql

from dipdup.exceptions import ConfigurationError
from dipdup.exceptions import FrameworkException
from dipdup.exceptions import InvalidModelsError
from dipdup.utils import iter_files
from dipdup.utils import pascal_to_snake

_logger = logging.getLogger(__name__)

DEFAULT_CONNECTION_NAME = 'default'
HEAD_STATUS_TIMEOUT = 3 * 60


AsyncpgClient = AsyncpgDBClient
SupportedClient = SqliteClient | AsyncpgClient


def get_connection() -> SupportedClient:
    return cast(SupportedClient, connections.get(DEFAULT_CONNECTION_NAME))


def set_connection(conn: SupportedClient) -> None:
    connections.set(DEFAULT_CONNECTION_NAME, conn)


@asynccontextmanager
async def tortoise_wrapper(
    url: str,
    models: str | None = None,
    timeout: int = 60,
    decimal_precision: int | None = None,
    unsafe_sqlite: bool = False,
) -> AsyncIterator[None]:
    """Initialize Tortoise with internal and project models, close connections when done"""
    if ':memory' in url:
        _logger.warning('Using in-memory database; data will be lost on exit')
    if '/tmp/' in url:
        _logger.warning('Using tmpfs database; data will be lost on reboot')

    model_modules: dict[str, Iterable[str | ModuleType]] = {
        'int_models': ['dipdup.models'],
    }
    if models:
        if not models.endswith('.models'):
            models += '.models'
        model_modules['models'] = [models]

    # NOTE: Must be called before entering Tortoise context
    decimal_precision = decimal_precision or guess_decimal_precision(models)
    set_decimal_precision(decimal_precision)
    prepare_models(models)

    try:
        for attempt in range(timeout):
            try:
                await Tortoise.init(
                    db_url=url,
                    modules=model_modules,
                )

                conn = get_connection()
                try:
                    await conn.execute_query('SELECT 1')
                except asyncpg.exceptions.InvalidPasswordError as e:
                    raise ConfigurationError(f'{e.__class__.__name__}: {e}') from e

                if unsafe_sqlite:
                    _logger.warning('Unsafe SQLite mode enabled; database integrity is not guaranteed!')
                    await conn.execute_script('PRAGMA foreign_keys = OFF')
                    await conn.execute_script('PRAGMA synchronous = OFF')
                    await conn.execute_script('PRAGMA journal_mode = OFF')

            # FIXME: Poor logging
            except (OSError, asyncpg.exceptions.CannotConnectNowError):
                _logger.warning("Can't establish database connection, attempt %s/%s", attempt, timeout)
                if attempt == timeout - 1:
                    raise
                await asyncio.sleep(1)
            else:
                break
        yield
    finally:
        await Tortoise.close_connections()


from dipdup.models import CachedModel
from dipdup.models import Model


def is_model_class(obj: Any) -> bool:
    """Is subclass of tortoise.Model, but not the base class"""

    if not isinstance(obj, type):
        return False
    if not issubclass(obj, TortoiseModel):
        return False
    if obj in (TortoiseModel, Model):
        return False
    if obj._meta.abstract:
        return False
    return True


def iter_models(package: str | None) -> Iterator[tuple[str, type[TortoiseModel]]]:
    """Iterate over built-in and project's models"""
    modules = [
        ('int_models', importlib.import_module('dipdup.models')),
    ]

    if package:
        if not package.endswith('.models'):
            package += '.models'
        modules.append(
            ('models', importlib.import_module(package)),
        )

    for app, module in modules:
        for attr in dir(module):
            if attr.startswith('_'):
                continue

            attr_value = getattr(module, attr)
            if is_model_class(attr_value):
                yield app, attr_value


def get_schema_hash(conn: SupportedClient) -> str:
    """Get hash of the current schema"""
    schema_sql = get_schema_sql(conn, False)
    # NOTE: Column order in generated CREATE TABLE expressions could differ, so drop commas and sort strings first.
    processed_schema_sql = '\n'.join(sorted(schema_sql.replace(',', '').split('\n'))).encode()
    return hashlib.sha256(processed_schema_sql).hexdigest()


async def execute_sql(
    conn: BaseDBAsyncClient,
    path: Path,
    *args: Any,
    **kwargs: Any,
) -> None:
    """Execute SQL script(s) with formatting"""
    for file in iter_files(path, ext='.sql'):
        _logger.info('Executing script `%s`', file.name)
        # NOTE: Usually string-formating SQL scripts is a very bad idea. But for indexers it's totally fine.
        sql = file.read().format(*args, **kwargs)
        for statement in sqlparse.split(sql):
            # NOTE: Ignore empty statements
            with suppress(AttributeError):
                await conn.execute_script(statement)


async def execute_sql_query(
    conn: SupportedClient,
    path: Path,
    *values: Any,
) -> Any:
    """Execute SQL query with arguments"""
    _logger.info('Executing query `%s`', path.name)
    sql = path.read_text()
    return await conn.execute_query(sql, list(values))


async def generate_schema(
    conn: SupportedClient,
    name: str,
) -> None:
    if isinstance(conn, AsyncpgClient):
        await pg_create_schema(conn, name)

    await Tortoise.generate_schemas()

    if isinstance(conn, AsyncpgClient):
        # NOTE: Create a view for monitoring head status
        sql_path = Path(__file__).parent / 'sql' / 'dipdup_head_status.sql'
        # TODO: Configurable interval
        await execute_sql(conn, sql_path, HEAD_STATUS_TIMEOUT)


async def _wipe_schema_postgres(
    conn: AsyncpgClient,
    schema_name: str,
    immune_tables: set[str],
) -> None:
    immune_schema_name = f'{schema_name}_immune'

    # NOTE: Create a truncate_schema function to trigger cascade deletion
    sql_path = Path(__file__).parent / 'sql' / 'truncate_schema.sql'
    await execute_sql(conn, sql_path, schema_name, immune_schema_name)

    # NOTE: Move immune tables to a separate schema - it's free!
    if immune_tables:
        await pg_create_schema(conn, immune_schema_name)
        for table in immune_tables:
            await pg_move_table(conn, table, schema_name, immune_schema_name)

    await conn.execute_script(f"SELECT truncate_schema('{schema_name}')")

    if immune_tables:
        for table in immune_tables:
            await pg_move_table(conn, table, immune_schema_name, schema_name)
        await pg_drop_schema(conn, immune_schema_name)


async def _wipe_schema_sqlite(
    conn: SqliteClient,
    path: str,
    immune_tables: set[str],
) -> None:
    if path == ':memory:':
        raise FrameworkException('Attempted to wipe in-memory database; that makes no sense')

    # NOTE: Dropping huge tables and deleting from them is slow and I/O heavy in SQLite. It's better to save the tables of interest
    # elsewhere and drop the whole database. First, create a new database and attach it to the current connection:
    immune_path, namespace = f'{path}.immune', 'immune'
    await conn.execute_script(f'ATTACH DATABASE "{immune_path}" AS {namespace}')

    # NOTE: Copy immune tables to the new database.
    master_query = 'SELECT name, type FROM sqlite_master'
    result = await conn.execute_query(master_query)
    for name, type_ in result[1]:
        if type_ != 'table' or name not in immune_tables:
            continue

        expr = f'CREATE TABLE {namespace}.{name} AS SELECT * FROM {name}'
        _logger.info('Executing `%s`', expr)
        await conn.execute_script(expr)

    # NOTE: Now the weirdest part - swap the databases when the program exits and all connections are closed.
    def _finish_wipe() -> None:
        _logger.info('Restoring immune tables')
        Path(immune_path).replace(path)

    atexit.register(_finish_wipe)


async def wipe_schema(
    conn: SupportedClient,
    schema_name: str,
    immune_tables: set[str],
) -> None:
    """Truncate schema preserving immune tables. Executes in a transaction"""
    async with conn._in_transaction() as conn:
        if isinstance(conn, SqliteClient):
            await _wipe_schema_sqlite(conn, schema_name, immune_tables)
        elif isinstance(conn, AsyncpgClient):
            await _wipe_schema_postgres(conn, schema_name, immune_tables)
        else:
            raise NotImplementedError


async def pg_create_schema(conn: AsyncpgClient, name: str) -> None:
    """Create PostgreSQL schema if not exists"""
    await conn.execute_script(f'CREATE SCHEMA IF NOT EXISTS {name}')


async def pg_drop_schema(conn: AsyncpgClient, name: str) -> None:
    await conn.execute_script(f'DROP SCHEMA IF EXISTS {name}')


async def pg_move_table(conn: AsyncpgClient, name: str, schema: str, new_schema: str) -> None:
    """Move table from one schema to another"""
    await conn.execute_script(f'ALTER TABLE {schema}.{name} SET SCHEMA {new_schema}')


def prepare_models(package: str | None) -> None:
    """Prepare TortoiseORM models to use with DipDup.
    Generate missing table names, validate models, increase decimal precision if needed.
    """
    # NOTE: Circular imports
    import dipdup.fields
    import dipdup.models

    # NOTE: Required for pytest-xdist. Models with the same name in different packages cause conflicts otherwise.
    EXECUTOR_CACHE.clear()

    db_tables: set[str] = set()

    for app, model in iter_models(package):
        # NOTE: Enforce our class for user models
        if app != 'int_models' and not issubclass(model, dipdup.models.Model):
            raise InvalidModelsError(
                (
                    'Project models must be subclassed from `dipdup.models.Model`.'
                    '\n\n'
                    'Replace `from tortoise import Model` import with `from dipdup.models import Model`.'
                ),
                model,
            )

        # NOTE: Generate missing table names before Tortoise does
        if not model._meta.db_table:
            model._meta.db_table = pascal_to_snake(model.__name__)

        if model._meta.db_table not in db_tables:
            db_tables.add(model._meta.db_table)
        else:
            raise InvalidModelsError(
                'Table name is duplicated or reserved. Make sure that all models have unique table names.',
                model,
            )

        # NOTE: Enforce tables in snake_case
        table_name = model._meta.db_table
        if table_name != pascal_to_snake(table_name):
            raise InvalidModelsError(
                'Table name must be in snake_case.',
                model,
            )

        for field in model._meta.fields_map.values():
            # NOTE: Ensure that field is imported from dipdup.fields
            if app != 'int_models' and not field.__module__.startswith('dipdup.fields'):
                raise InvalidModelsError(
                    'Model fields must be imported from `dipdup.fields`.',
                    model,
                    field.model_field_name,
                )

            # NOTE: Enforce fields in snake_case
            field_name = field.model_field_name
            if field_name != pascal_to_snake(field_name):
                raise InvalidModelsError(
                    'Model fields must be in snake_case.',
                    model,
                    field_name,
                )

            # NOTE: Enforce unique field names to avoid GraphQL issues
            if field_name == table_name:
                raise InvalidModelsError(
                    'Model field names must differ from the table name.',
                    model,
                    field_name,
                )

            # NOTE: The same for backward relations
            if isinstance(field, dipdup.fields.ForeignKeyField) and field.related_name == table_name:
                raise InvalidModelsError(
                    'Model field names must differ from the table name.',
                    model,
                    f'related_name={field.related_name}',
                )


async def preload_cached_models(package: str | None) -> None:
    from dipdup.performance import caches

    for _, model in iter_models(package):
        if issubclass(model, CachedModel):
            caches.add_model(model)
            await model.preload()


def guess_decimal_precision(package: str | None) -> int:
    """Guess decimal precision from project models.

    Doesn't work for realy big numbers.
    """
    prec = 0
    for _, model in iter_models(package):
        for field in model._meta.fields_map.values():
            if not isinstance(field, DecimalField):
                continue
            prec = max(prec, field.max_digits)
    return prec


def set_decimal_precision(prec: int) -> None:
    """Set decimal precision for the current and all future threads"""
    decimal_context = decimal.getcontext()
    if prec <= decimal_context.prec:
        return

    _logger.warning('Decimal context precision has been updated: %s -> %s', decimal_context.prec, prec)
    decimal_context.prec = prec
    # NOTE: DefaultContext is used for new threads
    decimal.DefaultContext.prec = prec
    decimal.setcontext(decimal_context)
