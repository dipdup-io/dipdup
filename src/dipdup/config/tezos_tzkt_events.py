from __future__ import annotations

from dataclasses import field
from typing import Any
from typing import Iterator
from typing import Literal

from pydantic.dataclasses import dataclass

from dipdup.config import ContractConfig
from dipdup.config import HandlerConfig
from dipdup.config import IndexConfig
from dipdup.config.tzkt import TzktDatasourceConfig
from dipdup.exceptions import ConfigInitializationException
from dipdup.utils import import_from
from dipdup.utils import pascal_to_snake
from dipdup.utils import snake_to_pascal


@dataclass
class EventHandlerConfig(HandlerConfig, kind='handler'):
    """Event handler config

    :param callback: Callback name
    :param contract: Contract which emits event
    :param tag: Event tag
    """

    contract: ContractConfig
    tag: str

    def __post_init_post_parse__(self) -> None:
        super().__post_init_post_parse__()
        self._event_type_cls: type[Any] | None = None

    @property
    def event_type_cls(self) -> type:
        if self._event_type_cls is None:
            raise ConfigInitializationException
        return self._event_type_cls

    def initialize_event_type(self, package: str) -> None:
        """Resolve imports and initialize key and value type classes"""
        tag = pascal_to_snake(self.tag.replace('.', '_'))

        module_name = f'{package}.types.{self.contract.module_name}.event.{tag}'
        cls_name = snake_to_pascal(f'{tag}_payload')
        self._event_type_cls = import_from(module_name, cls_name)

    def iter_imports(self, package: str) -> Iterator[tuple[str, str]]:
        yield 'dipdup.context', 'HandlerContext'
        yield 'dipdup.models.tzkt', 'Event'
        yield package, 'models as models'

        event_cls = snake_to_pascal(self.tag + '_payload')
        event_module = pascal_to_snake(self.tag)
        module_name = self.contract.module_name
        yield f'{package}.types.{module_name}.event.{event_module}', event_cls

    def iter_arguments(self) -> Iterator[tuple[str, str]]:
        event_cls = snake_to_pascal(self.tag + '_payload')
        yield 'ctx', 'HandlerContext'
        yield 'event', f'Event[{event_cls}]'


@dataclass
class UnknownEventHandlerConfig(HandlerConfig, kind='handler'):
    """Unknown event handler config

    :param callback: Callback name
    :param contract: Contract which emits event
    """

    contract: ContractConfig

    def iter_imports(self, package: str) -> Iterator[tuple[str, str]]:
        yield 'dipdup.context', 'HandlerContext'
        yield 'dipdup.models.tzkt', 'UnknownEvent'
        yield package, 'models as models'

    def iter_arguments(self) -> Iterator[tuple[str, str]]:
        yield 'ctx', 'HandlerContext'
        yield 'event', 'UnknownEvent'


EventHandlerConfigU = EventHandlerConfig | UnknownEventHandlerConfig


@dataclass
class EventIndexConfig(IndexConfig):
    """Event index config

    :param kind: Index kind
    :param datasource: Datasource config
    :param handlers: Event handlers
    :param first_level: First block level to index
    :param last_level: Last block level to index
    """

    kind: Literal['tezos.tzkt.events']
    datasource: TzktDatasourceConfig
    handlers: tuple[EventHandlerConfigU, ...] = field(default_factory=tuple)

    first_level: int = 0
    last_level: int = 0

    def import_objects(self, package: str) -> None:
        for handler_config in self.handlers:
            handler_config.initialize_callback_fn(package)
