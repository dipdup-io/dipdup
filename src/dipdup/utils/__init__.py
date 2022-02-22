import asyncio
import importlib
import logging
import os
import pkgutil
import time
import types
from collections import defaultdict
from contextlib import asynccontextmanager
from functools import partial
from functools import reduce
from logging import Logger
from os import listdir
from os import makedirs
from os.path import dirname
from os.path import exists
from os.path import getsize
from os.path import join
from typing import Any
from typing import Callable
from typing import DefaultDict
from typing import Dict
from typing import Iterator
from typing import List
from typing import Optional
from typing import Sequence
from typing import TextIO
from typing import TypeVar
from unittest import skip

import humps  # type: ignore
from genericpath import isdir
from genericpath import isfile

from dipdup.exceptions import HandlerImportError

_logger = logging.getLogger('dipdup.utils')


def import_submodules(package: str) -> Dict[str, types.ModuleType]:
    """Recursively import all submodules of a package"""
    results = {}
    for _, name, is_pkg in pkgutil.walk_packages((package,)):
        full_name = package + '.' + name
        results[full_name] = importlib.import_module(full_name)
        if is_pkg:
            results.update(import_submodules(full_name))
    return results


@asynccontextmanager
async def slowdown(seconds: int):
    """Sleep if nested block was executed faster than X seconds"""
    started_at = time.time()
    yield
    finished_at = time.time()
    time_spent = finished_at - started_at
    if time_spent < seconds:
        await asyncio.sleep(seconds - time_spent)


def snake_to_pascal(value: str) -> str:
    """humps wrapper for Python imports"""
    return humps.pascalize(value.replace('.', '_'))


def pascal_to_snake(value: str, strip_dots: bool = True) -> str:
    """humps wrapper for Python imports"""
    if strip_dots:
        value = value.replace('.', '_')
    return humps.depascalize(value).replace('__', '_')


def split_by_chunks(input_: List[Any], size: int) -> Iterator[List[Any]]:
    i = 0
    while i < len(input_):
        yield input_[i : i + size]
        i += size


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


# TODO: Cache me
def iter_files(path: str, ext: Optional[str] = None) -> Iterator[TextIO]:
    """Iterate over files in a directory. Or a single file. Sort alphabetically, filter by extension, skip empty files."""
    if not exists(path):
        return
    elif isfile(path):
        paths = iter(path)
    elif isdir(path):
        paths = map(partial(join, path), sorted(listdir(path)))
    else:
        raise RuntimeError(f'Path `{path}` exists but is neither a file nor a directory')

    for path in paths:
        if ext and not path.endswith(ext):
            continue
        if not exists(path):
            continue
        if not getsize(path):
            continue
        with open(path) as file:
            yield file


def mkdir_p(path: str) -> None:
    """Create directory tree, ignore if already exists"""
    if not exists(path):
        _logger.info('Creating directory `%s`', path)
        makedirs(path)


def touch(path: str) -> None:
    """Create empty file, ignore if already exists"""
    mkdir_p(dirname(path))
    if not exists(path):
        _logger.info('Creating file `%s`', path)
        open(path, 'a').close()


def write(path: str, content: str, overwrite: bool = False) -> bool:
    """Write content to file, create directory tree if necessary"""
    mkdir_p(dirname(path))
    if exists(path) and not overwrite:
        return False
    _logger.info('Writing into file `%s`', path)
    with open(path, 'w') as file:
        file.write(content)
    return True


def import_from(module: str, obj: str) -> Any:
    """Import object from module, raise HandlerImportError on failure"""
    try:
        return getattr(importlib.import_module(module), obj)
    except (ImportError, AttributeError) as e:
        raise HandlerImportError(module, obj) from e


def remove_prefix(text: str, prefix: str) -> str:
    """Remove prefix and strip underscores"""
    if text.startswith(prefix):
        text = text[len(prefix) :]
    return text.strip('_')


def skip_ci(fn):
    if os.environ.get('CI'):
        return skip('CI environment, skipping')(fn)
    return fn


def exclude_none(config_json):
    if isinstance(config_json, (list, tuple)):
        return [exclude_none(i) for i in config_json if i is not None]
    if isinstance(config_json, dict):
        return {k: exclude_none(v) for k, v in config_json.items() if v is not None}
    return config_json
