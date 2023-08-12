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
from dipdup.subscriptions import Subscription
from dipdup.utils import pascal_to_snake
from dipdup.utils import snake_to_pascal


@dataclass
class SubsquidEventsHandlerConfig(HandlerConfig):
    """Subsquid event handler

    :param contract: EVM contract
    :param name: Method name
    """

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
    """Subsquid datasource config

    :param kind: Always 'evm.subsquid.events'
    :param datasource: Subsquid datasource
    :param handlers: Event handlers
    :param abi: One or more `evm.abi` datasource(s) for the same network
    :param first_level: Level to start indexing from
    :param last_level: Level to stop indexing and disable this index
    """

    kind: Literal['evm.subsquid.events']
    datasource: SubsquidDatasourceConfig
    handlers: tuple[SubsquidEventsHandlerConfig, ...] = field(default_factory=tuple)
    abi: AbiDatasourceConfig | tuple[AbiDatasourceConfig, ...] | None = None

    first_level: int = 0
    last_level: int = 0

    def get_subscriptions(self) -> set[Subscription]:
        subs: set[Subscription] = set()
        subs.add(EvmNodeNewHeadsSubscription())
        # FIXME: Be selective
        subs.add(EvmNodeLogsSubscription())
        subs.add(EvmNodeSyncingSubscription())
        return subs
