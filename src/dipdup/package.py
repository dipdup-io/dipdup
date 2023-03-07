from pathlib import Path
from typing import Awaitable
from typing import Callable

from pydantic import BaseModel

from dipdup.exceptions import ProjectImportError
from dipdup.utils import import_from
from dipdup.utils import import_submodules
from dipdup.utils import pascal_to_snake
from dipdup.utils import touch

KEEP_MARKER = '.keep'
PYTHON_MARKER = '__init__.py'
PEP_561_MARKER = 'py.typed'
MODELS_MODULE = 'models.py'


IMPORTED_TYPES: dict[str, type[BaseModel]] = {}
IMPORTED_CALLBACKS: dict[str, Callable[..., Awaitable[None]]] = {}


class DipDupPackage:
    def __init__(self, root: Path, debug: bool = False) -> None:
        self.root = root
        self.debug = debug
        self.name = root.name
        self.abi = root / 'abi'
        self.schemas = root / 'schemas'
        self.types = root / 'types'
        self.handlers = root / 'handlers'
        self.hooks = root / 'hooks'
        self.sql = root / 'sql'
        self.graphql = root / 'graphql'
        self.hasura = root / 'hasura'

    def create(self) -> None:
        """Create Python package skeleton if not exists"""
        self.pre_init()

        touch(self.root / PYTHON_MARKER)
        touch(self.root / PEP_561_MARKER)
        touch(self.root / MODELS_MODULE)

        touch(self.abi / KEEP_MARKER)
        touch(self.schemas / KEEP_MARKER)

        touch(self.types / PYTHON_MARKER)
        touch(self.handlers / PYTHON_MARKER)
        touch(self.hooks / PYTHON_MARKER)

        touch(self.sql / KEEP_MARKER)
        touch(self.graphql / KEEP_MARKER)
        touch(self.hasura / KEEP_MARKER)

    def pre_init(self) -> None:
        if self.name != pascal_to_snake(self.name):
            raise ProjectImportError(f'`{self.name}` is not a valid Python package name')
        if self.root.exists() and not self.root.is_dir():
            raise ProjectImportError(f'`{self.root}` must be a directory')

    def post_init(self) -> None:
        if not self.debug:
            for path in self.schemas.glob('**/*.json'):
                path.unlink()

    def verify(self) -> None:
        import_submodules(self.name)

    def get_type(self, typename: str, module: str, name: str) -> type[BaseModel]:
        path = f'{self.name}.types.{typename}.{module}'
        key = f'{path}.{name}'
        if key not in IMPORTED_TYPES:
            type_ = IMPORTED_TYPES[key] = import_from(path, name)
            if not isinstance(type_, type):
                raise ProjectImportError(f'`{key}` is not a valid type')
        return IMPORTED_TYPES[key]

    def get_callback(self, kind: str, module: str, name: str) -> Callable[..., Awaitable[None]]:
        path = f'{self.name}.{kind}.{module}'
        key = f'{path}.{name}'
        if key not in IMPORTED_CALLBACKS:
            callback = IMPORTED_CALLBACKS[key] = import_from(path, name)
            if not callable(callback):
                raise ProjectImportError(f'`{key}` is not a valid callback')
        return IMPORTED_CALLBACKS[key]

    # def get_evm_abi_path(self, name: str) -> Path:
    #     path = self.abi / f'{name}.json'
    #     if not path.exists():
    #         raise ProjectImportError(f'`{path}` does not exist')
    #     return orjson.loads(path.read_text())
