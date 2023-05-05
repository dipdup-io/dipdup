from functools import lru_cache
from pathlib import Path
from typing import Any
from typing import Awaitable
from typing import Callable
from typing import cast

import orjson
from pydantic import BaseModel
from pydantic.dataclasses import dataclass

from dipdup.exceptions import ProjectImportError
from dipdup.utils import import_from
from dipdup.utils import import_submodules
from dipdup.utils import pascal_to_snake
from dipdup.utils import touch

KEEP_MARKER = '.keep'
PYTHON_MARKER = '__init__.py'
PEP_561_MARKER = 'py.typed'
MODELS_MODULE = 'models.py'


@dataclass(frozen=True)
class EventAbiExtra:
    name: str
    topic0: str
    inputs: tuple[tuple[str, bool], ...]


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

        self.get_callback = lru_cache(maxsize=2 ^ 13)(self.get_callback)  # type: ignore[method-assign]
        self.get_type = lru_cache(maxsize=2 ^ 13)(self.get_type)  # type: ignore[method-assign]
        self.get_evm_abi = lru_cache(maxsize=2 ^ 13)(self.get_evm_abi)  # type: ignore[method-assign]
        self.get_evm_events = lru_cache(maxsize=2 ^ 13)(self.get_evm_events)  # type: ignore[method-assign]
        self.get_evm_topics = lru_cache(maxsize=2 ^ 13)(self.get_evm_topics)  # type: ignore[method-assign]

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
        type_ = import_from(path, name)
        if not isinstance(type_, type):
            raise ProjectImportError(f'`{path}.{name}` is not a valid type')
        return type_

    def get_callback(self, kind: str, module: str, name: str) -> Callable[..., Awaitable[None]]:
        path = f'{self.name}.{kind}.{module}'
        callback = import_from(path, name)
        if not callable(callback):
            raise ProjectImportError(f'`{path}.{name}` is not a valid callback')
        return cast(Callable[..., Awaitable[None]], callback)

    def get_evm_abi(self, typename: str) -> dict[str, Any]:
        path = self.abi / typename / 'abi.json'
        if not path.exists():
            raise ProjectImportError(f'`{path}` does not exist')
        return cast(dict[str, Any], orjson.loads(path.read_text()))

    def get_evm_events(self, typename: str) -> dict[str, EventAbiExtra]:
        path = self.abi / typename / 'events.json'
        if not path.exists():
            raise ProjectImportError(f'`{path}` does not exist')
        extra_json = orjson.loads(path.read_text())
        return {k: EventAbiExtra(**v) for k, v in extra_json.items()}

    def get_evm_topics(self, typename: str) -> dict[str, str]:
        return {k: v.topic0 for k, v in self.get_evm_events(typename).items()}
