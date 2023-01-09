import importlib
import logging
import pkgutil
import types
from collections import defaultdict
from decimal import Decimal
from functools import reduce
from logging import Logger
from pathlib import Path
from typing import Any
from typing import Callable
from typing import DefaultDict
from typing import Dict
from typing import Iterator
from typing import List
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import TextIO
from typing import TypeVar
from typing import Union

import orjson
from humps import main as humps

from dipdup.exceptions import FrameworkException
from dipdup.exceptions import ProjectImportError


def import_submodules(package: str) -> Dict[str, types.ModuleType]:
    """Recursively import all submodules of a package"""
    results = {}
    for _, name, is_pkg in pkgutil.walk_packages((package,)):
        full_name = package + '.' + name
        results[full_name] = importlib.import_module(full_name)
        if is_pkg:
            results.update(import_submodules(full_name))
    return results


def snake_to_pascal(value: str) -> str:
    """humps wrapper for Python imports"""
    value = value.replace('.', '_')
    # NOTE: Special case, humps returns uppercase otherwise
    if value.isupper():
        value = value.lower()
    return humps.pascalize(value)


def pascal_to_snake(value: str, strip_dots: bool = True) -> str:
    """humps wrapper for Python imports"""
    if strip_dots:
        value = value.replace('.', '_')
    # NOTE: Special case, humps returns uppercase otherwise
    if value.isupper():
        value = value.lower()
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
        lambda grp, val: grp[key(val)].append(val) or grp,  # type: ignore[func-returns-value]
        seq,
        defaultdict(list),
    )


class FormattedLogger(Logger):
    """Logger wrapper with additional formatting"""

    def __init__(self, name: str, fmt: Optional[str] = None) -> None:
        self.logger = logging.getLogger(name)
        self.fmt = fmt

    def __getattr__(self, name: str) -> Any:
        if name == '_log':
            return self._log
        return getattr(self.logger, name)

    def _log(
        self,
        level: int,
        msg: object,
        args: Any,
        exc_info: Optional[
            Union[
                None,
                bool,
                Union[
                    tuple[type[BaseException], BaseException, Optional[types.TracebackType]], tuple[None, None, None]
                ],
                BaseException,
            ]
        ] = None,
        extra: Mapping[str, Any] | None = None,
        stack_info: bool = False,
        stacklevel: int = 1,
    ) -> None:
        if self.fmt:
            msg = self.fmt.format(msg)
        self.logger._log(level, msg, args, exc_info, extra, stack_info, stacklevel)


def iter_files(path: Path, ext: Optional[str] = None) -> Iterator[TextIO]:
    """Iterate over files in a directory. Or a single file. Sort alphabetically, filter by extension, skip empty files."""
    if not path.exists() and ext:
        path = Path(f'{path}{ext}')
    if not path.exists():
        return
    elif path.is_file():
        paths = [path]
    elif path.is_dir():
        paths = sorted(path.glob('**/*'))
    else:
        raise FrameworkException(f'Path `{path}` exists but is neither a file nor a directory')

    for path in paths:
        if ext and path.suffix != ext:
            continue
        if not path.exists():
            continue
        if not path.stat().st_size:
            continue
        with open(path) as file:
            yield file


def import_from(module: str, obj: str) -> Any:
    """Import object from module, raise ProjectImportError on failure"""
    try:
        return getattr(importlib.import_module(module), obj)
    except (ImportError, AttributeError) as e:
        raise ProjectImportError(module, obj) from e


def exclude_none(config_json: Any) -> Any:
    if isinstance(config_json, (list, tuple)):
        return [exclude_none(i) for i in config_json if i is not None]
    if isinstance(config_json, dict):
        return {k: exclude_none(v) for k, v in config_json.items() if v is not None}
    return config_json


def json_dumps_decimals(obj: Any) -> str:
    def _default(obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return str(obj)
        raise TypeError

    return orjson.dumps(obj, default=_default).decode()
