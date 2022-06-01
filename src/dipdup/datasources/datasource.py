import logging
from abc import abstractmethod
from typing import Awaitable
from typing import Callable
from typing import Optional
from typing import Set
from typing import Tuple

from aiohttp.hdrs import METH_GET

from dipdup.config import HTTPConfig
from dipdup.datasources.subscription import HeadSubscription
from dipdup.datasources.subscription import Subscription
from dipdup.datasources.subscription import SubscriptionManager
from dipdup.enums import MessageType
from dipdup.http import HTTPGateway
from dipdup.models import BigMapData
from dipdup.models import HeadBlockData
from dipdup.models import OperationData
from dipdup.utils import FormattedLogger

_logger = logging.getLogger('dipdup.datasource')


EmptyCallbackT = Callable[[], Awaitable[None]]
HeadCallbackT = Callable[['IndexDatasource', HeadBlockData], Awaitable[None]]
OperationsCallbackT = Callable[['IndexDatasource', Tuple[OperationData, ...]], Awaitable[None]]
BigMapsCallbackT = Callable[['IndexDatasource', Tuple[BigMapData, ...]], Awaitable[None]]
RollbackCallbackT = Callable[['IndexDatasource', MessageType, int, int], Awaitable[None]]


class Datasource(HTTPGateway):
    def __init__(self, url: str, http_config: HTTPConfig) -> None:
        super().__init__(url, http_config)
        self._logger = _logger

    @abstractmethod
    async def run(self) -> None:
        ...

    def set_logger(self, name: str) -> None:
        self._logger = FormattedLogger(self._logger.name, name + ': {}')


class HttpDatasource(Datasource):
    _default_http_config = HTTPConfig(
        cache=True,
        retry_count=5,
        retry_sleep=1,
        ratelimit_rate=0,
        ratelimit_period=0,
    )

    def __init__(self, url: str, http_config: Optional[HTTPConfig] = None) -> None:
        super().__init__(url, self._default_http_config.merge(http_config))
        self._logger = _logger

    async def get(self, url: str, cache: bool = False, weight: int = 1, **kwargs):
        return await self.request(METH_GET, url, cache, weight, **kwargs)

    async def run(self) -> None:
        pass


# TODO: Generic interface
class GraphQLDatasource(Datasource):
    ...


class IndexDatasource(Datasource):
    def __init__(self, url: str, http_config: HTTPConfig, merge_subscriptions: bool = False) -> None:
        super().__init__(url, http_config)
        self._on_connected_callbacks: Set[EmptyCallbackT] = set()
        self._on_disconnected_callbacks: Set[EmptyCallbackT] = set()
        self._on_head_callbacks: Set[HeadCallbackT] = set()
        self._on_operations_callbacks: Set[OperationsCallbackT] = set()
        self._on_big_maps_callbacks: Set[BigMapsCallbackT] = set()
        self._on_rollback_callbacks: Set[RollbackCallbackT] = set()
        self._subscriptions: SubscriptionManager = SubscriptionManager(merge_subscriptions)
        self._subscriptions.add(HeadSubscription())
        self._network: Optional[str] = None

    @property
    def name(self) -> str:
        return self._http._url

    @property
    def network(self) -> str:
        if not self._network:
            raise RuntimeError('Network is not set')
        return self._network

    @abstractmethod
    async def subscribe(self) -> None:
        ...

    def call_on_head(self, fn: HeadCallbackT) -> None:
        self._on_head_callbacks.add(fn)

    def call_on_operations(self, fn: OperationsCallbackT) -> None:
        self._on_operations_callbacks.add(fn)

    def call_on_big_maps(self, fn: BigMapsCallbackT) -> None:
        self._on_big_maps_callbacks.add(fn)

    def call_on_rollback(self, fn: RollbackCallbackT) -> None:
        self._on_rollback_callbacks.add(fn)

    def call_on_connected(self, fn: EmptyCallbackT) -> None:
        self._on_connected_callbacks.add(fn)

    def call_on_disconnected(self, fn: EmptyCallbackT) -> None:
        self._on_disconnected_callbacks.add(fn)

    async def emit_head(self, head: HeadBlockData) -> None:
        for fn in self._on_head_callbacks:
            await fn(self, head)

    async def emit_operations(self, operations: Tuple[OperationData, ...]) -> None:
        for fn in self._on_operations_callbacks:
            await fn(self, operations)

    async def emit_big_maps(self, big_maps: Tuple[BigMapData, ...]) -> None:
        for fn in self._on_big_maps_callbacks:
            await fn(self, big_maps)

    async def emit_rollback(self, type_: MessageType, from_level: int, to_level: int) -> None:
        for fn in self._on_rollback_callbacks:
            await fn(self, type_, from_level, to_level)

    async def emit_connected(self) -> None:
        for fn in self._on_connected_callbacks:
            await fn()

    async def emit_disconnected(self) -> None:
        for fn in self._on_disconnected_callbacks:
            await fn()

    def set_network(self, network: str) -> None:
        if self._network:
            raise RuntimeError('Network is already set')
        self._network = network

    def set_sync_level(self, subscription: Optional[Subscription], level: int) -> None:
        self._subscriptions.set_sync_level(subscription, level)

    def get_sync_level(self, subscription: Subscription) -> Optional[int]:
        return self._subscriptions.get_sync_level(subscription)
