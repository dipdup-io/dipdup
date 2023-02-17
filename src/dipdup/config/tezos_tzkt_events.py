from __future__ import annotations

from dataclasses import field
from typing import Iterator
from typing import Literal

from pydantic.dataclasses import dataclass

from dipdup.config import ContractConfig
from dipdup.config import HandlerConfig
from dipdup.config.tezos_tzkt import TzktDatasourceConfig
from dipdup.config.tezos_tzkt import TzktIndexConfig
from dipdup.utils import pascal_to_snake
from dipdup.utils import snake_to_pascal


@dataclass
class TzktEventsHandlerConfig(HandlerConfig):
    """Event handler config

    :param callback: Callback name
    :param contract: Contract which emits event
    :param tag: Event tag
    """

    contract: ContractConfig
    tag: str

    def iter_imports(self, package: str) -> Iterator[tuple[str, str]]:
        yield 'dipdup.context', 'HandlerContext'
        yield 'dipdup.models.tezos_tzkt', 'TzktEvent'
        yield package, 'models as models'

        event_cls = snake_to_pascal(self.tag + '_payload')
        event_module = pascal_to_snake(self.tag)
        module_name = self.contract.module_name
        yield f'{package}.types.{module_name}.event.{event_module}', event_cls

    def iter_arguments(self) -> Iterator[tuple[str, str]]:
        event_cls = snake_to_pascal(self.tag + '_payload')
        yield 'ctx', 'HandlerContext'
        yield 'event', f'TzktEvent[{event_cls}]'


@dataclass
class TzktEventsUnknownEventHandlerConfig(HandlerConfig):
    """Unknown event handler config

    :param callback: Callback name
    :param contract: Contract which emits event
    """

    contract: ContractConfig

    def iter_imports(self, package: str) -> Iterator[tuple[str, str]]:
        yield 'dipdup.context', 'HandlerContext'
        yield 'dipdup.models.tezos_tzkt', 'TzktUnknownEvent'
        yield package, 'models as models'

    def iter_arguments(self) -> Iterator[tuple[str, str]]:
        yield 'ctx', 'HandlerContext'
        yield 'event', 'TzktUnknownEvent'


TzktEventsHandlerConfigU = TzktEventsHandlerConfig | TzktEventsUnknownEventHandlerConfig


@dataclass
class TzktEventsIndexConfig(TzktIndexConfig):
    """Event index config

    :param kind: always `tezos.tzkt.events`
    :param datasource: Datasource config
    :param handlers: Event handlers
    :param first_level: First block level to index
    :param last_level: Last block level to index
    """

    kind: Literal['tezos.tzkt.events']
    datasource: TzktDatasourceConfig
    handlers: tuple[TzktEventsHandlerConfigU, ...] = field(default_factory=tuple)

    first_level: int = 0
    last_level: int = 0
