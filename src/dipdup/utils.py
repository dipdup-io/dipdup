import asyncio
import decimal
import errno
import importlib
import logging
import pkgutil
import time
import types
from collections import defaultdict
from contextlib import asynccontextmanager
from functools import reduce
from logging import Logger
from os import listdir, makedirs
from os.path import dirname, exists, getsize, join
from typing import Any, AsyncIterator, Callable, DefaultDict, Dict, Iterator, List, Optional, Sequence, TextIO, Tuple, Type, TypeVar

import humps  # type: ignore
from tortoise import Tortoise
from tortoise.backends.asyncpg.client import AsyncpgDBClient
from tortoise.backends.base.client import TransactionContext
from tortoise.backends.sqlite.client import SqliteClient
from tortoise.fields import DecimalField
from tortoise.models import Model
from tortoise.transactions import in_transaction

from dipdup.exceptions import HandlerImportError

_logger = logging.getLogger('dipdup.utils')


def import_submodules(package: str) -> Dict[str, types.ModuleType]:
    """Import all submodules of a module, recursively, including subpackages"""
    results = {}
    for _, name, is_pkg in pkgutil.walk_packages((package,)):
        full_name = package + '.' + name
        results[full_name] = importlib.import_module(full_name)
        if is_pkg:
            results.update(import_submodules(full_name))
    return results


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
    return humps.pascalize(value)


def pascal_to_snake(value: str) -> str:
    return humps.depascalize(value.replace('.', '_')).replace('__', '_')


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


def is_model_class(obj: Any) -> bool:
    """Is subclass of tortoise.Model, but not the base class"""
    return isinstance(obj, type) and issubclass(obj, Model) and obj != Model and not getattr(obj.Meta, 'abstract', False)


# TODO: Cache me
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


_T = TypeVar('_T')
_TT = TypeVar('_TT')


def groupby(seq: Sequence[_T], key: Callable[[Any], _TT]) -> DefaultDict[_TT, List[_T]]:
    """Group by key into defaultdict"""
    return reduce(
        lambda grp, val: grp[key(val)].append(val) or grp,  # type: ignore
        seq,
        defaultdict(list),
    )


class FormattedLogger(Logger):
    """Logger wrapper with additional formatting"""

    def __init__(self, name: str, fmt: Optional[str] = None) -> None:
        self.logger = logging.getLogger(name)
        self.fmt = fmt

    def __getattr__(self, name: str) -> Callable:
        if name == '_log':
            return self._log
        return getattr(self.logger, name)

    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False, stacklevel=1):
        if self.fmt:
            msg = self.fmt.format(msg)
        self.logger._log(level, msg, args, exc_info, extra, stack_info, stacklevel)


def iter_files(path: str, ext: Optional[str] = None) -> Iterator[TextIO]:
    """Iterate over files in a directory. Sort alphabetically, filter by extension, skip empty files."""
    if not exists(path):
        raise StopIteration
    for filename in sorted(listdir(path)):
        filepath = join(path, filename)
        if ext and not filename.endswith(ext):
            continue
        if not getsize(filepath):
            continue

        with open(filepath) as file:
            yield file


def mkdir_p(path: str) -> None:
    """Create directory tree, ignore if already exists"""
    try:
        makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


def touch(path: str) -> None:
    """Create empty file, ignore if already exists"""
    mkdir_p(dirname(path))
    try:
        open(path, 'a').close()
    except IOError as e:
        if e.errno != errno.EEXIST:
            raise


def write(path: str, content: str, overwrite: bool = False) -> bool:
    """Write content to file, create directory tree if necessary"""
    mkdir_p(dirname(path))
    if exists(path) and not overwrite:
        return False
    with open(path, 'w') as file:
        file.write(content)
    return True


def import_from(module: str, obj: str) -> Any:
    """Import object from module, raise HandlerImportError on failure"""
    try:
        return getattr(importlib.import_module(module), obj)
    except (ImportError, AttributeError) as e:
        raise HandlerImportError(module, obj) from e
