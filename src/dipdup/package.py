from collections import deque
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
PEP_561_MARKER = 'py.typed'
DEFAULT_ENV = '.env.default'


_branch = '│   '
_tee = '├── '
_last = '└── '


def _get_pointers(content_length: int) -> tuple[str, ...]:
    return (_tee,) * (content_length - 1) + (_last,)


def draw_package_tree(root: Path, project_tree: dict[str, tuple[Path, ...]]) -> tuple[str, ...]:
    lines: deque[str] = deque()
    lines.append(root.name)
    pointers = _get_pointers(len(project_tree) - 1)
    for pointer, (section, paths) in zip(pointers, project_tree.items()):
        lines.append(pointer + section)
        for inner_pointer, path in zip(_get_pointers(len(paths)), sorted(paths)):
            relative_path = path.relative_to(root / section)
            lines.append(_branch + inner_pointer + relative_path.as_posix())

    return tuple(lines)


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

        # NOTE: Package sections with .keep markers
        self.abi = root / 'abi'
        self.configs = root / 'configs'
        self.deploy = root / 'deploy'
        self.graphql = root / 'graphql'
        self.handlers = root / 'handlers'
        self.hasura = root / 'hasura'
        self.hooks = root / 'hooks'
        self.models = root / 'models'
        self.sql = root / 'sql'
        self.types = root / 'types'

        # NOTE: Shared directories; not a part of package
        self._xdg_shared_dir = Path.home() / '.local' / 'share' / 'dipdup'
        self.schemas = self._xdg_shared_dir / 'schemas' / self.name

        # NOTE: Finally, internal in-memory stuff
        self._callbacks: dict[str, Callable[..., Awaitable[Any]]] = {}
        self._types: dict[str, type[BaseModel]] = {}
        self._evm_abis: dict[str, dict[str, dict[str, Any]]] = {}
        self._evm_events: dict[str, dict[str, EventAbiExtra]] = {}
        self._evm_topics: dict[str, dict[str, str]] = {}

    @property
    def skel(self) -> dict[Path, str | None]:
        return {
            self.abi: '**/*.json',
            self.configs: '**/*.y[a]ml',
            self.deploy: '**/*',
            self.graphql: '**/*.graphql',
            self.handlers: '**/*.py',
            self.hasura: '**/*.json',
            self.hooks: '**/*.py',
            self.models: '**/*.py',
            self.sql: '**/*.sql',
            self.types: '**/*.py',
        }

    def discover(self) -> dict[str, tuple[Path, ...]]:
        tree = {}
        for path, exp in self.skel.items():
            tree[path.name] = tuple(path.glob(exp)) if exp else ()
        return tree

    def create(self) -> None:
        """Create Python package skeleton if not exists"""
        self.pre_init()

        touch(self.root / PEP_561_MARKER)
        touch(self.root / '__init__.py')

        for path in self.skel:
            touch(path / KEEP_MARKER)

    def pre_init(self) -> None:
        if self.name != pascal_to_snake(self.name):
            raise ProjectImportError(f'`{self.name}` is not a valid Python package name')
        if self.root.exists() and not self.root.is_dir():
            raise ProjectImportError(f'`{self.root}` must be a directory')

    def post_init(self) -> None:
        ...

    def verify(self) -> None:
        import_submodules(self.name)

    def get_type(self, typename: str, module: str, name: str) -> type[BaseModel]:
        key = f'{typename}{module}{name}'
        if (type_ := self._types.get(key)) is None:
            path = f'{self.name}.types.{typename}.{module}'
            type_ = import_from(path, name)
            if not isinstance(type_, type):
                raise ProjectImportError(f'`{path}.{name}` is not a valid type')
            self._types[key] = type_
        return type_

    def get_callback(self, kind: str, module: str, name: str) -> Callable[..., Awaitable[None]]:
        key = f'{kind}{module}{name}'
        if (callback := self._callbacks.get(key)) is None:
            path = f'{self.name}.{kind}.{module}'
            callback = import_from(path, name)
            if not callable(callback):
                raise ProjectImportError(f'`{path}.{name}` is not a valid callback')
            self._callbacks[key] = callback
        return cast(Callable[..., Awaitable[None]], callback)

    def get_evm_abi(self, typename: str) -> dict[str, Any]:
        if (abi := self._evm_abis.get(typename)) is None:
            path = self.abi / typename / 'abi.json'
            if not path.exists():
                raise ProjectImportError(f'`{path}` does not exist')
            abi = cast(dict[str, Any], orjson.loads(path.read_text()))
            self._evm_abis[typename] = abi
        return abi

    def get_evm_events(self, typename: str) -> dict[str, EventAbiExtra]:
        if (events := self._evm_events.get(typename)) is None:
            path = self.abi / typename / 'events.json'
            if not path.exists():
                raise ProjectImportError(f'`{path}` does not exist')
            extra_json = orjson.loads(path.read_text())
            events = {k: EventAbiExtra(**v) for k, v in extra_json.items()}
            self._evm_events[typename] = events
        return events

    def get_evm_topics(self, typename: str) -> dict[str, str]:
        if (topics := self._evm_topics.get(typename)) is None:
            topics = {k: v.topic0 for k, v in self.get_evm_events(typename).items()}
            self._evm_topics[typename] = topics
        return topics
