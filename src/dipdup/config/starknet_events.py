

from collections.abc import Iterator
from typing import Literal

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from dipdup.config import Alias
from dipdup.config import HandlerConfig
from dipdup.config.starknet import StarknetContractConfig
from dipdup.config.starknet import StarknetIndexConfig
from dipdup.utils import pascal_to_snake
from dipdup.utils import snake_to_pascal


@dataclass(config=ConfigDict(extra='forbid'), kw_only=True)
class StarknetEventsHandlerConfig(HandlerConfig):
    """Subsquid event handler

    :param callback: Callback name
    :param contract: Starknet contract
    :param name: Event name
    """

    contract: Alias[StarknetContractConfig]
    name: str

    def iter_imports(self, package: str) -> Iterator[tuple[str, str]]:
        yield 'dipdup.context', 'HandlerContext'
        yield 'dipdup.models.starknet', 'StarknetEvent'
        yield package, 'models as models'

        event_cls = snake_to_pascal(self.name) + 'Payload'
        event_module = pascal_to_snake(self.name)
        module_name = self.contract.module_name
        yield f'{package}.types.{module_name}.starknet_events.{event_module}', event_cls

    def iter_arguments(self) -> Iterator[tuple[str, str]]:
        event_cls = snake_to_pascal(self.name) + 'Payload'
        yield 'ctx', 'HandlerContext'
        yield 'event', f'StarknetEvent[{event_cls}]'


@dataclass(config=ConfigDict(extra='forbid'), kw_only=True)
class StarknetEventsIndexConfig(StarknetIndexConfig):
    """Starknet events index config

    :param kind: Always 'starknet.events'
    :param handlers: Event handlers
    """

    kind: Literal['starknet.events']
    handlers: tuple[StarknetEventsHandlerConfig, ...]
