from __future__ import annotations

from dataclasses import field
from typing import Iterator
from typing import Literal

from pydantic.dataclasses import dataclass

from dipdup.config import AbiDatasourceConfig
from dipdup.config import ContractConfig
from dipdup.config import HandlerConfig
from dipdup.config import IndexConfig
from dipdup.config.evm_subsquid import SubsquidDatasourceConfig
from dipdup.utils import pascal_to_snake
from dipdup.utils import snake_to_pascal


@dataclass
class SubsquidEventsHandlerConfig(HandlerConfig):
    contract: ContractConfig
    name: str

    def iter_imports(self, package: str) -> Iterator[tuple[str, str]]:
        yield 'dipdup.context', 'HandlerContext'
        yield 'dipdup.models.evm_subsquid', 'SubsquidEvent'
        yield package, 'models as models'

        event_cls = snake_to_pascal(self.name + '_payload')
        event_module = pascal_to_snake(self.name)
        module_name = self.contract.module_name
        yield f'{package}.types.{module_name}.event.{event_module}', event_cls

    def iter_arguments(self) -> Iterator[tuple[str, str]]:
        event_cls = snake_to_pascal(self.name + '_payload')
        yield 'ctx', 'HandlerContext'
        yield 'event', f'SubsquidEvent[{event_cls}]'


@dataclass
class SubsquidEventsIndexConfig(IndexConfig):

    kind: Literal['evm.subsquid.events']
    datasource: SubsquidDatasourceConfig
    handlers: tuple[SubsquidEventsHandlerConfig, ...] = field(default_factory=tuple)
    abi: tuple[AbiDatasourceConfig, ...] = field(default_factory=tuple)

    first_level: int = 0
    last_level: int = 0
