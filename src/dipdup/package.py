import logging
from collections import deque
from collections.abc import Awaitable
from collections.abc import Callable
from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import TypedDict
from typing import cast

from pydantic import BaseModel

from dipdup import env
from dipdup.exceptions import ProjectPackageError
from dipdup.project import Answers
from dipdup.project import answers_from_replay
from dipdup.utils import import_from
from dipdup.utils import import_submodules
from dipdup.utils import pascal_to_snake
from dipdup.utils import touch

if TYPE_CHECKING:
    from starknet_py.cairo.data_types import CairoType  # type: ignore[import-untyped]
    from starknet_py.serialization import PayloadSerializer  # type: ignore[import-untyped]


KEEP_MARKER = '.keep'
PACKAGE_MARKER = '__init__.py'
PEP_561_MARKER = 'py.typed'
DEFAULT_ENV = '.env.default'


EVM_ABI_JSON = 'abi.json'
CAIRO_ABI_JSON = 'cairo_abi.json'

_branch = '│   '
_tee = '├── '
_last = '└── '

_logger = logging.getLogger(__name__)


def _get_pointers(content_length: int) -> tuple[str, ...]:
    return (_tee,) * (content_length - 1) + (_last,)


def draw_package_tree(root: Path, project_tree: dict[str, tuple[Path, ...]]) -> tuple[str, ...]:
    lines: deque[str] = deque()
    pointers = _get_pointers(len(project_tree) - 1)
    for pointer, (section, paths) in zip(pointers, project_tree.items(), strict=False):
        lines.append(pointer + section)
        for inner_pointer, path in zip(_get_pointers(len(paths)), sorted(paths), strict=False):
            relative_path = path.relative_to(root / section)
            lines.append(_branch + inner_pointer + relative_path.as_posix())

    return tuple(lines)


class ConvertedEventAbi(TypedDict):
    name: str
    topic0: str
    inputs: tuple[tuple[str, bool], ...]
    topic_count: int


class ConvertedMethodAbi(TypedDict):
    name: str
    sighash: str
    inputs: tuple[dict[str, str], ...]
    outputs: tuple[dict[str, str], ...]


class ConvertedEvmAbi(TypedDict):
    events: dict[str, ConvertedEventAbi]
    methods: dict[str, ConvertedMethodAbi]


class ConvertedEventCairoAbi(TypedDict):
    name: str
    event_identifier: str
    members: dict[str, 'CairoType']
    serializer: 'PayloadSerializer'


class ConvertedCairoAbi(TypedDict):
    events: dict[str, ConvertedEventCairoAbi]


class DipDupPackage:
    def __init__(self, root: Path) -> None:
        _logger.info('Loading package `%s` from `%s`', root.name, root)

        self.root = root
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
        self._replay: Answers | None = None
        self._callbacks: dict[str, Callable[..., Awaitable[Any]]] = {}
        self._types: dict[str, type[BaseModel]] = {}
        self._converted_evm_abis: dict[str, ConvertedEvmAbi] = {}
        self._converted_cairo_abis: dict[str, ConvertedCairoAbi] = {}

    @property
    def cairo_abi_paths(self) -> Generator[Any, None, None]:
        return self.abi.glob(f'**/{CAIRO_ABI_JSON}')

    @property
    def evm_abi_paths(self) -> Generator[Any, None, None]:
        return self.abi.glob(f'**/{EVM_ABI_JSON}')

    @property
    def replay(self) -> Answers | None:
        if not self._replay and (self.root / 'configs' / 'replay.yaml').exists():
            self._replay = answers_from_replay(self.root / 'configs' / 'replay.yaml')
        return self._replay

    @property
    def skel(self) -> dict[Path, str | None]:
        return {
            # NOTE: Package sections
            self.abi: '**/*.json',
            self.configs: '**/*.y[a]ml',
            self.deploy: '**/*[Dockerfile|.env.default|yml|yaml]',
            self.graphql: '**/*.graphql',
            self.handlers: '**/*.py',
            self.hasura: '**/*.json',
            self.hooks: '**/*.py',
            self.models: '**/*.py',
            self.sql: '**/*.sql',
            self.types: '**/*.py',
            # NOTE: Python metadata
            Path(PEP_561_MARKER): None,
            Path(PACKAGE_MARKER): None,
        }

    def in_migration(self) -> bool:
        for path in self.root.iterdir():
            if path.name.endswith('.old'):
                return True
        return False

    def tree(self) -> dict[str, tuple[Path, ...]]:
        tree = {}
        for path, exp in self.skel.items():
            tree[path.name] = tuple(path.glob(exp)) if exp else ()
        return tree

    def initialize(self) -> None:
        """Create Python package skeleton if not exists"""
        self._pre_init()

        _logger.debug('Updating `%s` package structure', self.name)
        for path, glob in self.skel.items():
            if glob:
                touch(path / KEEP_MARKER)
            else:
                touch(self.root / path)
        self.schemas.mkdir(parents=True, exist_ok=True)

        self._post_init()

    def _pre_init(self) -> None:
        if self.name != pascal_to_snake(self.name):
            raise ProjectPackageError(f'`{self.name}` is not a valid Python package name')
        if self.root.exists() and not self.root.is_dir():
            raise ProjectPackageError(f'`{self.root}` exists and not a directory')

    def _post_init(self) -> None:
        # NOTE: Allows plain package structure to be imported
        if self.root != Path.cwd() or env.NO_SYMLINK:
            return

        symlink_path = self.root.joinpath(self.name)
        if symlink_path.exists() and not symlink_path.is_symlink():
            raise ProjectPackageError(f'`{symlink_path}` exists and not a symlink')
        if not symlink_path.exists():
            symlink_path.symlink_to('.', True)

    def verify(self) -> None:
        _logger.debug('Verifying `%s` package', self.root)
        import_submodules(f'{self.name}.handlers')
        import_submodules(f'{self.name}.hooks')
        import_submodules(f'{self.name}.types')

    def get_type(self, typename: str, module: str, name: str) -> type[BaseModel]:
        key = f'{typename}{module}{name}'
        if (type_ := self._types.get(key)) is None:
            path = f'{self.name}.types.{typename}.{module}'
            type_ = import_from(path, name)
            if not isinstance(type_, type):
                raise ProjectPackageError(f'`{path}.{name}` is not a valid type')
            self._types[key] = type_
        return type_

    def get_callback(self, kind: str, module: str, name: str) -> Callable[..., Awaitable[None]]:
        key = f'{kind}{module}{name}'
        if (callback := self._callbacks.get(key)) is None:
            path = f'{self.name}.{kind}.{module}'
            callback = import_from(path, name)
            if not callable(callback):
                raise ProjectPackageError(f'`{path}.{name}` is not a valid callback')
            self._callbacks[key] = callback
        return cast(Callable[..., Awaitable[None]], callback)

    def get_converted_evm_abi(self, typename: str) -> ConvertedEvmAbi:
        if not self._converted_evm_abis:
            from dipdup.codegen.evm import convert_abi

            self._converted_evm_abis = convert_abi(self)
        return self._converted_evm_abis[typename]

    def get_converted_starknet_abi(self, typename: str) -> ConvertedCairoAbi:
        if not self._converted_cairo_abis:
            from dipdup.codegen.starknet import convert_abi

            self._converted_cairo_abis = convert_abi(self)
        return self._converted_cairo_abis[typename]
