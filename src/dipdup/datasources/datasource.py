from abc import abstractmethod
from collections import defaultdict
from copy import copy
from enum import Enum
from functools import partial
from typing import Awaitable, DefaultDict, List, Optional, Protocol, Set

from pydantic.dataclasses import dataclass
from pydantic.fields import Field
from pyee import AsyncIOEventEmitter  # type: ignore

from dipdup.config import HTTPConfig
from dipdup.http import HTTPGateway
from dipdup.models import BigMapData, HeadBlockData, OperationData


class EventType(Enum):
    operations = 'operatitions'
    big_maps = 'big_maps'
    rollback = 'rollback'
    head = 'head'


class OperationsCallback(Protocol):
    def __call__(self, datasource: 'IndexDatasource', operations: List[OperationData], block: HeadBlockData) -> Awaitable[None]:
        ...


class BigMapsCallback(Protocol):
    def __call__(self, datasource: 'IndexDatasource', big_maps: List[BigMapData]) -> Awaitable[None]:
        ...


class RollbackCallback(Protocol):
    def __call__(self, datasource: 'IndexDatasource', from_level: int, to_level: int) -> Awaitable[None]:
        ...


class HeadCallback(Protocol):
    def __call__(self, datasource: 'IndexDatasource', block: HeadBlockData) -> Awaitable[None]:
        ...


class Datasource(HTTPGateway):
    @abstractmethod
    async def run(self) -> None:
        ...


class IndexDatasource(Datasource, AsyncIOEventEmitter):
    def __init__(self, url: str, http_config: Optional[HTTPConfig] = None) -> None:
        HTTPGateway.__init__(self, url, http_config)
        AsyncIOEventEmitter.__init__(self)

    def on(self, event, f=None) -> None:
        raise RuntimeError('Do not use `on` directly')

    def emit(self, event: str, *args, **kwargs) -> None:
        if event not in ('new_listener', 'error'):
            raise RuntimeError('Do not use `emit` directly')
        super().emit(event, *args, **kwargs)

    def on_operations(self, fn: OperationsCallback) -> None:
        super().on(EventType.operations, fn)

    def on_big_maps(self, fn: BigMapsCallback) -> None:
        super().on(EventType.big_maps, fn)

    def on_rollback(self, fn: RollbackCallback) -> None:
        super().on(EventType.rollback, fn)

    def on_head(self, fn: HeadCallback) -> None:
        super().on(EventType.head, fn)

    def emit_operations(self, operations: List[OperationData], block: HeadBlockData) -> None:
        super().emit(EventType.operations, datasource=self, operations=operations, block=block)

    def emit_big_maps(self, big_maps: List[BigMapData]) -> None:
        super().emit(EventType.big_maps, datasource=self, big_maps=big_maps)

    def emit_rollback(self, from_level: int, to_level: int) -> None:
        super().emit(EventType.rollback, datasource=self, from_level=from_level, to_level=to_level)

    def emit_head(self, block: HeadBlockData) -> None:
        super().emit(EventType.head, datasource=self, block=block)


@dataclass
class Subscriptions:
    address_transactions: Set[str] = Field(default_factory=set)
    originations: bool = False
    head: bool = False
    big_maps: DefaultDict[str, Set[str]] = Field(default_factory=partial(defaultdict, set))

    def get_pending(self, active_subscriptions: 'Subscriptions') -> 'Subscriptions':
        return Subscriptions(
            address_transactions=self.address_transactions.difference(active_subscriptions.address_transactions),
            originations=not active_subscriptions.originations,
            head=not active_subscriptions.head,
            big_maps=defaultdict(set, {k: self.big_maps[k] for k in set(self.big_maps) - set(active_subscriptions.big_maps)}),
        )


class SubscriptionManager:
    def __init__(self) -> None:
        self._subscriptions: Subscriptions = Subscriptions()
        self._active_subscriptions: Subscriptions = Subscriptions()

    def add_address_transaction_subscription(self, address: str) -> None:
        self._subscriptions.address_transactions.add(address)

    def add_origination_subscription(self) -> None:
        self._subscriptions.originations = True

    def add_head_subscription(self) -> None:
        self._subscriptions.head = True

    def add_big_map_subscription(self, address: str, paths: Set[str]) -> None:
        self._subscriptions.big_maps[address] = self._subscriptions.big_maps[address] | paths

    def get_pending(self) -> Subscriptions:
        pending_subscriptions = self._subscriptions.get_pending(self._active_subscriptions)
        return pending_subscriptions

    def commit(self) -> None:
        self._active_subscriptions = copy(self._subscriptions)

    def reset(self) -> None:
        self._active_subscriptions = Subscriptions()
