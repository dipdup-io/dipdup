import importlib
import logging
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Awaitable, Callable
from typing import Any
from typing import Type
from typing import TypeVar
from typing import Union

from pydantic import BaseModel
from pydantic import ValidationError

from dipdup.exceptions import InvalidDataError
from dipdup.exceptions import ProjectImportError
from dipdup.utils import pascal_to_snake
from dipdup.utils import snake_to_pascal

if TYPE_CHECKING:
    from jinja2 import Template

_logger = logging.getLogger('dipdup.codegen')


def touch(path: Path) -> None:
    """Create empty file, ignore if already exists"""
    if not path.parent.exists():
        _logger.info('Creating directory `%s`', path.parent)
        path.parent.mkdir(parents=True, exist_ok=True)

    if not path.is_file():
        _logger.info('Creating file `%s`', path)
        path.touch()


def write(path: Path, content: Union[str, bytes], overwrite: bool = False) -> bool:
    """Write content to file, create directory tree if necessary"""
    if not path.parent.exists():
        _logger.info('Creating directory `%s`', path.parent)
        path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists() and not overwrite:
        return False

    _logger.info('Writing into file `%s`', path)
    if isinstance(content, str):
        content = content.encode()
    path.write_bytes(content)
    return True


@cache
def load_template(*path: str) -> 'Template':
    """Load template from path relative to dipdup package"""
    from jinja2 import Template

    full_path = Path(__file__).parent.parent.joinpath(*path)
    return Template(full_path.read_text())


ObjectT = TypeVar('ObjectT', bound=BaseModel)


def parse_object(type_: Type[ObjectT], data: Any) -> ObjectT:
    try:
        return type_.parse_obj(data)
    except ValidationError as e:
        msg = f'Failed to parse: {e.errors()}'
        raise InvalidDataError(msg, type_, data) from e


def import_from(module: str, obj: str) -> Any:
    """Import object from module, raise ProjectImportError on failure"""
    try:
        return getattr(importlib.import_module(module), obj)
    except (ImportError, AttributeError) as e:
        raise ProjectImportError(module, obj) from e


def import_storage_type(self, package: str, module_name: str) -> type[BaseModel]:
    # _logger.debug('Registering `%s` storage type', module_name)
    cls_name = snake_to_pascal(module_name) + 'Storage'
    module_name = f'{package}.types.{module_name}.storage'
    return import_from(module_name, cls_name)


def import_parameter_type(self, package: str, typename: str, entrypoint: str) -> type[BaseModel]:
    # _logger.debug('Registering parameter type for entrypoint `%s`', entrypoint)
    entrypoint = entrypoint.lstrip('_')
    module_name = f'{package}.types.{typename}.parameter.{pascal_to_snake(entrypoint)}'
    cls_name = snake_to_pascal(entrypoint) + 'Parameter'
    return import_from(module_name, cls_name)


def initialize_event_type(self, package: str, module_name: str, tag: str) -> None:
    """Resolve imports and initialize key and value type classes"""
    # _logger.debug('Registering event types for tag `%s`', tag)
    tag = pascal_to_snake(tag.replace('.', '_'))

    module_name = f'{package}.types.{module_name}.event.{tag}'
    cls_name = snake_to_pascal(f'{tag}_payload')
    return import_from(module_name, cls_name)


def import_callback_fn(self, package: str, kind: str, callback: str) -> Callable[..., Awaitable[None]]:
    # _logger.debug('Registering %s callback `%s`', kind, callback)
    module_name = f'{package}.{kind}s.{callback}'
    fn_name = callback.rsplit('.', 1)[-1]
    return import_from(module_name, fn_name)
