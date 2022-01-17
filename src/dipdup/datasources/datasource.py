import logging
from abc import abstractmethod
from typing import Awaitable
from typing import Callable
from typing import Optional
from typing import Set
from typing import Tuple

from dipdup.config import HTTPConfig
from dipdup.datasources.subscription import HeadSubscription
from dipdup.datasources.subscription import Subscription
from dipdup.datasources.subscription import SubscriptionManager
from dipdup.http import HTTPGateway
from dipdup.models import BigMapData
from dipdup.models import HeadBlockData
from dipdup.models import OperationData
from dipdup.utils import FormattedLogger

_logger = logging.getLogger('dipdup.datasource')


HeadCallbackT = Callable[['IndexDatasource', HeadBlockData], Awaitable[None]]
OperationsCallbackT = Callable[['IndexDatasource', Tuple[OperationData, ...]], Awaitable[None]]
BigMapsCallbackT = Callable[['IndexDatasource', Tuple[BigMapData, ...]], Awaitable[None]]
RollbackCallbackT = Callable[['IndexDatasource', int, int], Awaitable[None]]


class Datasource(HTTPGateway):
    def __init__(self, url: str, http_config: HTTPConfig) -> None:
        super().__init__(url, http_config)
        self._logger = _logger

    @abstractmethod
    async def run(self) -> None:
        ...

    def set_logger(self, name: str) -> None:
        self._logger = FormattedLogger(self._logger.name, name + ': {}')


# TODO: Generic interface
class GraphQLDatasource(Datasource):
    ...


class IndexDatasource(Datasource):
    def __init__(self, url: str, http_config: HTTPConfig, merge_subscriptions: bool = False) -> None:
        super().__init__(url, http_config)
        self._on_head: Set[HeadCallbackT] = set()
        self._on_operations: Set[OperationsCallbackT] = set()
        self._on_big_maps: Set[BigMapsCallbackT] = set()
        self._on_rollback: Set[RollbackCallbackT] = set()
        self._subscriptions: SubscriptionManager = SubscriptionManager(merge_subscriptions)
        self._subscriptions.add(HeadSubscription())

    @property
    def name(self) -> str:
        return self._http._url

    @abstractmethod
    async def subscribe(self) -> None:
        ...

    def on_head(self, fn: HeadCallbackT) -> None:
        self._on_head.add(fn)

    def on_operations(self, fn: OperationsCallbackT) -> None:
        self._on_operations.add(fn)

    def on_big_maps(self, fn: BigMapsCallbackT) -> None:
        self._on_big_maps.add(fn)

    def on_rollback(self, fn: RollbackCallbackT) -> None:
        self._on_rollback.add(fn)

    async def emit_head(self, head: HeadBlockData) -> None:
        for fn in self._on_head:
            await fn(self, head)

    async def emit_operations(self, operations: Tuple[OperationData, ...]) -> None:
        for fn in self._on_operations:
            await fn(self, operations)

    async def emit_big_maps(self, big_maps: Tuple[BigMapData, ...]) -> None:
        for fn in self._on_big_maps:
            await fn(self, big_maps)

    async def emit_rollback(self, from_level: int, to_level: int) -> None:
        for fn in self._on_rollback:
            await fn(self, from_level, to_level)

    def set_sync_level(self, subscription: Optional[Subscription], level: int) -> None:
        self._subscriptions.set_sync_level(subscription, level)

    def get_sync_level(self, subscription: Subscription) -> Optional[int]:
        return self._subscriptions.get_sync_level(subscription)
