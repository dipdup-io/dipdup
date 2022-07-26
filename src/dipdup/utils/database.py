import asyncio
import decimal
import hashlib
import importlib
import logging
from contextlib import asynccontextmanager
from contextlib import suppress
from os.path import dirname
from os.path import join
from pathlib import Path
from typing import Any
from typing import AsyncIterator
from typing import Dict
from typing import Iterable
from typing import Iterator
from typing import Optional
from typing import Set
from typing import Tuple
from typing import Type
from typing import Union

import sqlparse  # type: ignore
from tortoise import Model as TortoiseModel
from tortoise import ModuleType
from tortoise import Tortoise
from tortoise import connections
from tortoise.backends.asyncpg.client import AsyncpgDBClient
from tortoise.backends.base.client import BaseDBAsyncClient
from tortoise.backends.sqlite.client import SqliteClient
from tortoise.fields import DecimalField
from tortoise.utils import get_schema_sql

from dipdup.exceptions import DatabaseConfigurationError
from dipdup.utils import iter_files
from dipdup.utils import pascal_to_snake

_logger = logging.getLogger('dipdup.database')
_truncate_schema_sql = Path(join(dirname(__file__), 'truncate_schema.sql')).read_text()

DEFAULT_CONNECTION_NAME = 'default'


def get_connection() -> BaseDBAsyncClient:
    return connections.get(DEFAULT_CONNECTION_NAME)


def set_connection(conn: BaseDBAsyncClient) -> None:
    connections.set(DEFAULT_CONNECTION_NAME, conn)


@asynccontextmanager
async def tortoise_wrapper(url: str, models: Optional[str] = None, timeout: int = 60) -> AsyncIterator:
    """Initialize Tortoise with internal and project models, close connections when done"""
    model_modules: Dict[str, Iterable[Union[str, ModuleType]]] = {
        'int_models': ['dipdup.models'],
    }
    if models:
        if not models.endswith('.models'):
            models += '.models'
        model_modules['models'] = [models]

    # NOTE: Must be called before entering Tortoise context
    prepare_models(models)

    try:
        for attempt in range(timeout):
            try:
                await Tortoise.init(
                    db_url=url,
                    modules=model_modules,
                )

                # FIXME: Wait for the connection to be ready, required since 0.19.0
                conn = get_connection()
                await conn.execute_query('SELECT 1')
            except OSError:
                _logger.warning('Can\'t establish database connection, attempt %s/%s', attempt, timeout)
                if attempt == timeout - 1:
                    raise
                await asyncio.sleep(1)
            else:
                break
        yield
    finally:
        await Tortoise.close_connections()


def is_model_class(obj: Any) -> bool:
    """Is subclass of tortoise.Model, but not the base class"""
    from dipdup.models import Model

    return isinstance(obj, type) and issubclass(obj, TortoiseModel) and obj not in (TortoiseModel, Model)


def iter_models(package: Optional[str]) -> Iterator[Tuple[str, Type[TortoiseModel]]]:
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


def get_schema_hash(conn: BaseDBAsyncClient) -> str:
    """Get hash of the current schema"""
    schema_sql = get_schema_sql(conn, False)
    # NOTE: Column order could differ in two generated schemas for the same models, drop commas and sort strings to eliminate this
    processed_schema_sql = '\n'.join(sorted(schema_sql.replace(',', '').split('\n'))).encode()
    return hashlib.sha256(processed_schema_sql).hexdigest()


async def create_schema(conn: BaseDBAsyncClient, name: str) -> None:
    if isinstance(conn, SqliteClient):
        raise NotImplementedError

    await conn.execute_script(f'CREATE SCHEMA IF NOT EXISTS {name}')
    # NOTE: Recreate `truncate_schema` function on fresh schema
    await conn.execute_script(_truncate_schema_sql)


async def execute_sql_scripts(conn: BaseDBAsyncClient, path: str) -> None:
    for file in iter_files(path, '.sql'):
        _logger.info('Executing `%s`', file.name)
        sql = file.read()
        for statement in sqlparse.split(sql):
            # NOTE: Ignore empty statements
            with suppress(AttributeError):
                await conn.execute_script(statement)


async def generate_schema(conn: BaseDBAsyncClient, name: str) -> None:
    if isinstance(conn, SqliteClient):
        await Tortoise.generate_schemas()
    elif isinstance(conn, AsyncpgDBClient):
        await create_schema(conn, name)
        await Tortoise.generate_schemas()

        # NOTE: Apply built-in scripts before project ones
        sql_path = join(dirname(__file__), '..', 'sql', 'on_reindex')
        await execute_sql_scripts(conn, sql_path)
    else:
        raise NotImplementedError


async def truncate_schema(conn: BaseDBAsyncClient, name: str) -> None:
    if isinstance(conn, SqliteClient):
        raise NotImplementedError

    await conn.execute_script(_truncate_schema_sql)
    await conn.execute_script(f"SELECT truncate_schema('{name}')")


async def wipe_schema(conn: BaseDBAsyncClient, name: str, immune_tables: Set[str]) -> None:
    if isinstance(conn, SqliteClient):
        raise NotImplementedError

    immune_schema_name = f'{name}_immune'
    if immune_tables:
        await create_schema(conn, immune_schema_name)
        for table in immune_tables:
            await move_table(conn, table, name, immune_schema_name)

    await truncate_schema(conn, name)

    if immune_tables:
        for table in immune_tables:
            await move_table(conn, table, immune_schema_name, name)
        await drop_schema(conn, immune_schema_name)


async def drop_schema(conn: BaseDBAsyncClient, name: str) -> None:
    if isinstance(conn, SqliteClient):
        raise NotImplementedError

    await conn.execute_script(f'DROP SCHEMA IF EXISTS {name}')


async def move_table(conn: BaseDBAsyncClient, name: str, schema: str, new_schema: str) -> None:
    """Move table from one schema to another"""
    if isinstance(conn, SqliteClient):
        raise NotImplementedError

    await conn.execute_script(f'ALTER TABLE {schema}.{name} SET SCHEMA {new_schema}')


def prepare_models(package: Optional[str]) -> None:
    """Prepare TortoiseORM models to use with DipDup.
    Generate missing table names, validate models, increase decimal precision.
    """
    from dipdup.models import Model

    decimal_context = decimal.getcontext()
    prec = decimal_context.prec

    for app, model in iter_models(package):

        # NOTE: Enforce our class for user models
        if app == 'models' and not issubclass(model, Model):
            raise DatabaseConfigurationError('Project models must be subclassed from `dipdup.models.Model`', model)

        # NOTE: Generate missing table names before Tortoise does
        if not model._meta.db_table:
            model._meta.db_table = pascal_to_snake(model.__name__)

        # NOTE: Enforce tables in snake_case
        table_name = model._meta.db_table
        if table_name != pascal_to_snake(table_name):
            raise DatabaseConfigurationError('Table name must be in snake_case', model)

        for field in model._meta.fields_map.values():
            # NOTE: Enforce fields in snake_case
            field_name = field.model_field_name
            if field_name != pascal_to_snake(field_name):
                raise DatabaseConfigurationError('Model fields must be in snake_case', model)

            # NOTE: Enforce unique field names to avoid GraphQL issues
            if field_name == table_name:
                raise DatabaseConfigurationError('Model fields must differ from table name', model)

            # NOTE: Increase decimal precision if needed
            if isinstance(field, DecimalField):
                prec = max(prec, field.max_digits)

    # NOTE: Set new decimal precision
    if decimal_context.prec < prec:
        _logger.warning('Decimal context precision has been updated: %s -> %s', decimal_context.prec, prec)
        decimal_context.prec = prec

        # NOTE: DefaultContext is used for new threads
        decimal.DefaultContext.prec = prec
        decimal.setcontext(decimal_context)
