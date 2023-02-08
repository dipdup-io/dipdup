from __future__ import annotations

from typing import Any
from typing import Iterator
from typing import Literal

from pydantic.dataclasses import dataclass

from dipdup.config import ContractConfig
from dipdup.config import HandlerConfig
from dipdup.config.tezos_tzkt import TzktDatasourceConfig
from dipdup.config.tezos_tzkt import TzktIndexConfig
from dipdup.exceptions import ConfigInitializationException
from dipdup.models import SkipHistory
from dipdup.utils import import_from
from dipdup.utils import pascal_to_snake
from dipdup.utils import snake_to_pascal


@dataclass
class TzktBigMapsHandlerConfig(HandlerConfig, kind='handler'):
    """Big map handler config

    :param callback: Callback name
    :param contract: Contract to fetch big map from
    :param path: Path to big map (alphanumeric string with dots)
    """

    contract: ContractConfig
    path: str

    def __post_init_post_parse__(self) -> None:
        super().__post_init_post_parse__()
        self._key_type_cls: type[Any] | None = None
        self._value_type_cls: type[Any] | None = None

    @classmethod
    def format_key_import(cls, package: str, module_name: str, path: str) -> tuple[str, str]:
        key_cls = f'{snake_to_pascal(path)}Key'
        key_module = f'{pascal_to_snake(path)}_key'
        return f'{package}.types.{module_name}.big_map.{key_module}', key_cls

    @classmethod
    def format_value_import(cls, package: str, module_name: str, path: str) -> tuple[str, str]:
        value_cls = f'{snake_to_pascal(path)}Value'
        value_module = f'{pascal_to_snake(path)}_value'
        return f'{package}.types.{module_name}.big_map.{value_module}', value_cls

    @classmethod
    def format_big_map_diff_argument(cls, path: str) -> tuple[str, str]:
        key_cls = f'{snake_to_pascal(path)}Key'
        value_cls = f'{snake_to_pascal(path)}Value'
        return pascal_to_snake(path), f'TzktBigMapDiff[{key_cls}, {value_cls}]'

    def iter_imports(self, package: str) -> Iterator[tuple[str, str]]:
        yield 'dipdup.context', 'HandlerContext'
        yield 'dipdup.models.tezos_tzkt', 'TzktBigMapDiff'
        yield package, 'models as models'

        yield self.format_key_import(package, self.contract.module_name, self.path)
        yield self.format_value_import(package, self.contract.module_name, self.path)

    def iter_arguments(self) -> Iterator[tuple[str, str]]:
        yield 'ctx', 'HandlerContext'
        yield self.format_big_map_diff_argument(self.path)

    @property
    def key_type_cls(self) -> type:
        if self._key_type_cls is None:
            raise ConfigInitializationException
        return self._key_type_cls

    @property
    def value_type_cls(self) -> type:
        if self._value_type_cls is None:
            raise ConfigInitializationException
        return self._value_type_cls

    def initialize_big_map_type(self, package: str) -> None:
        """Resolve imports and initialize key and value type classes"""
        path = pascal_to_snake(self.path.replace('.', '_'))

        module_name = f'{package}.types.{self.contract.module_name}.big_map.{path}_key'
        cls_name = snake_to_pascal(path + '_key')
        self._key_type_cls = import_from(module_name, cls_name)

        module_name = f'{package}.types.{self.contract.module_name}.big_map.{path}_value'
        cls_name = snake_to_pascal(path + '_value')
        self._value_type_cls = import_from(module_name, cls_name)


@dataclass
class TzktBigMapsIndexConfig(TzktIndexConfig):
    """Big map index config

    :param kind: always `tezos.tzkt.big_maps`
    :param datasource: Index datasource to fetch big maps with
    :param handlers: Mapping of big map diff handlers
    :param skip_history: Fetch only current big map keys ignoring historical changes
    :param first_level: Level to start indexing from
    :param last_level: Level to stop indexing at
    """

    kind: Literal['tezos.tzkt.big_maps']
    datasource: TzktDatasourceConfig
    handlers: tuple[TzktBigMapsHandlerConfig, ...]

    skip_history: SkipHistory = SkipHistory.never

    first_level: int = 0
    last_level: int = 0

    @property
    def contracts(self) -> set[ContractConfig]:
        return {handler_config.contract for handler_config in self.handlers}

    @classmethod
    def strip(cls, config_dict: dict[str, Any]) -> None:
        super().strip(config_dict)
        config_dict.pop('skip_history', None)

    def import_objects(self, package: str) -> None:
        for handler_config in self.handlers:
            handler_config.initialize_callback_fn(package)
            handler_config.initialize_big_map_type(package)
