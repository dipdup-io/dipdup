from __future__ import annotations

from dataclasses import field
from typing import Iterator
from typing import Literal

from pydantic.dataclasses import dataclass

from dipdup.config import AbiDatasourceConfig
from dipdup.config import HandlerConfig
from dipdup.config import IndexConfig
from dipdup.config.evm import EvmContractConfig
from dipdup.config.evm_subsquid import SubsquidDatasourceConfig
from dipdup.models.evm_node import EvmNodeLogsSubscription
from dipdup.models.evm_node import EvmNodeNewHeadsSubscription
from dipdup.models.evm_node import EvmNodeSyncingSubscription
from dipdup.models.evm_subsquid import ArchiveSubscription
from dipdup.subscriptions import Subscription
from dipdup.utils import pascal_to_snake
from dipdup.utils import snake_to_pascal


@dataclass
class SubsquidEventsHandlerConfig(HandlerConfig):
    contract: EvmContractConfig
    name: str

    def iter_imports(self, package: str) -> Iterator[tuple[str, str]]:
        yield 'dipdup.context', 'HandlerContext'
        yield 'dipdup.models.evm_subsquid', 'SubsquidEvent'
        yield package, 'models as models'

        event_cls = snake_to_pascal(self.name)
        event_module = pascal_to_snake(self.name)
        module_name = self.contract.module_name
        yield f'{package}.types.{module_name}.evm_events.{event_module}', event_cls

    def iter_arguments(self) -> Iterator[tuple[str, str]]:
        event_cls = snake_to_pascal(self.name)
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

    def get_subscriptions(self) -> set[Subscription]:
        subs: set[Subscription] = set()
        subs.add(ArchiveSubscription())
        subs.add(EvmNodeNewHeadsSubscription())
        # FIXME: Be selective
        subs.add(EvmNodeLogsSubscription())
        subs.add(EvmNodeSyncingSubscription())
        return subs
