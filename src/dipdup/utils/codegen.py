import importlib
import logging
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import Awaitable
from typing import Callable
from typing import Type
from typing import TypeVar
from typing import Union
from typing import cast

from pydantic import BaseModel
from pydantic import ValidationError

from dipdup.exceptions import InvalidDataError
from dipdup.exceptions import ProjectImportError
from dipdup.utils import pascal_to_snake
from dipdup.utils import snake_to_pascal

KEEP_MARKER = '.keep'
PYTHON_MARKER = '__init__.py'
PEP_561_MARKER = 'py.typed'
MODELS_MODULE = 'models.py'
CALLBACK_TEMPLATE = 'callback.py.j2'

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


class DipDupPackage:
    def __init__(self, root: Path, name: str) -> None:
        self.root = root
        self.package = root.name
        self.models = root / MODELS_MODULE
        self.schemas = root / 'schemas'
        self.types = root / 'types'
        self.handlers = root / 'handlers'
        self.hooks = root / 'hooks'
        self.sql = root / 'sql'
        self.graphql = root / 'graphql'

    @classmethod
    def load(cls, root: Path) -> 'DipDupPackage':
        """Load package from root directory"""
        if not root.is_dir():
            raise ProjectImportError(str(root))
        return cls(root, root.name)

    def create(self) -> None:
        """Create Python package skeleton if not exists"""
        touch(self.root / PYTHON_MARKER)
        touch(self.root / PEP_561_MARKER)

        touch(self.types / PYTHON_MARKER)
        touch(self.handlers / PYTHON_MARKER)
        touch(self.hooks / PYTHON_MARKER)

        touch(self.sql / KEEP_MARKER)
        touch(self.graphql / KEEP_MARKER)

        if not self.models.is_file():
            template = load_template('templates', f'{MODELS_MODULE}.j2')
            models_code = template.render()
            write(self.models, models_code)

    def get_storage_type(self, typename: str) -> type[BaseModel]:
        cls_name = snake_to_pascal(typename) + 'Storage'
        module_name = f'{self.package}.types.{typename}.storage'
        return cast(
            type[BaseModel],
            import_from(module_name, cls_name),
        )

    def get_parameter_type(self, typename: str, entrypoint: str) -> type[BaseModel]:
        entrypoint = entrypoint.lstrip('_')
        module_name = f'{self.package}.types.{typename}.parameter.{pascal_to_snake(entrypoint)}'
        cls_name = snake_to_pascal(entrypoint) + 'Parameter'
        return cast(
            type[BaseModel],
            import_from(module_name, cls_name),
        )

    def get_event_type(self, typename: str, tag: str) -> type[BaseModel]:
        tag = pascal_to_snake(tag.replace('.', '_'))
        module_name = f'{self.package}.types.{typename}.event.{tag}'
        cls_name = snake_to_pascal(f'{tag}_payload')
        return cast(
            type[BaseModel],
            import_from(module_name, cls_name),
        )

    def get_big_map_key_type(self, typename: str, path: str) -> type[BaseModel]:
        path = pascal_to_snake(path.replace('.', '_'))
        module_name = f'{self.package}.types.{typename}.big_map.{path}_key'
        cls_name = snake_to_pascal(path + '_key')
        return cast(
            type[BaseModel],
            import_from(module_name, cls_name),
        )

    def get_big_map_value_type(self, typename: str, path: str) -> type[BaseModel]:
        path = pascal_to_snake(path.replace('.', '_'))
        module_name = f'{self.package}.types.{typename}.big_map.{path}_value'
        cls_name = snake_to_pascal(path + '_value')
        return cast(
            type[BaseModel],
            import_from(module_name, cls_name),
        )

    def get_callback_fn(self, kind: str, callback: str) -> Callable[..., Awaitable[None]]:
        module_name = f'{self.package}.{kind}s.{callback}'
        fn_name = callback.rsplit('.', 1)[-1]
        return cast(
            Callable[..., Awaitable[None]],
            import_from(module_name, fn_name),
        )
