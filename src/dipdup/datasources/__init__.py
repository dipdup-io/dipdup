from abc import abstractmethod
from collections.abc import Awaitable
from collections.abc import Callable
from typing import Any
from typing import Generic
from typing import TypeVar

from dipdup.config import DatasourceConfig
from dipdup.config import HttpConfig
from dipdup.config import IndexConfig
from dipdup.config import IndexDatasourceConfig
from dipdup.config import ResolvedHttpConfig
from dipdup.exceptions import FrameworkException
from dipdup.http import HTTPGateway
from dipdup.models import MessageType
from dipdup.subscriptions import Subscription
from dipdup.subscriptions import SubscriptionManager
from dipdup.utils import FormattedLogger

DatasourceConfigT = TypeVar('DatasourceConfigT', bound=DatasourceConfig)
IndexDatasourceConfigT = TypeVar('IndexDatasourceConfigT', bound=IndexDatasourceConfig)

EmptyCallback = Callable[[], Awaitable[None]]
RollbackCallback = Callable[['IndexDatasource[Any]', MessageType, int, int], Awaitable[None]]


class Datasource(HTTPGateway, Generic[DatasourceConfigT]):
    _default_http_config = HttpConfig()

    def __init__(self, config: DatasourceConfigT) -> None:
        self._config = config
        http_config = ResolvedHttpConfig.create(self._default_http_config, config.http)
        http_config.alias = http_config.alias or config.name
        super().__init__(
            url=config.url,
            http_config=http_config,
        )
        self._logger = FormattedLogger(__name__, config.name + ': {}')

    @abstractmethod
    async def run(self) -> None: ...

    @property
    def name(self) -> str:
        return self._config.name


class AbiDatasource(Datasource[DatasourceConfigT], Generic[DatasourceConfigT]):
    @abstractmethod
    async def get_abi(self, address: str) -> dict[str, Any]: ...


class IndexDatasource(Datasource[IndexDatasourceConfigT], Generic[IndexDatasourceConfigT]):
    def __init__(
        self,
        config: IndexDatasourceConfigT,
        merge_subscriptions: bool = False,
    ) -> None:
        super().__init__(config)
        self._subscriptions: SubscriptionManager = SubscriptionManager(merge_subscriptions)
        self._on_connected_callbacks: set[EmptyCallback] = set()
        self._on_disconnected_callbacks: set[EmptyCallback] = set()
        self._on_rollback_callbacks: set[RollbackCallback] = set()

    @abstractmethod
    async def subscribe(self) -> None: ...

    @abstractmethod
    async def initialize(self) -> None: ...

    def add_index(self, index_config: IndexConfig) -> None:
        """Register index config in internal mappings and matchers. Find and register subscriptions."""
        for subscription in index_config.get_subscriptions():
            self._subscriptions.add(subscription)

    def set_sync_level(self, subscription: Subscription | None, level: int) -> None:
        self._subscriptions.set_sync_level(subscription, level)

    def get_sync_level(self, subscription: Subscription) -> int | None:
        return self._subscriptions.get_sync_level(subscription)

    def call_on_connected(self, fn: EmptyCallback) -> None:
        self._on_connected_callbacks.add(fn)

    def call_on_disconnected(self, fn: EmptyCallback) -> None:
        self._on_disconnected_callbacks.add(fn)

    def call_on_rollback(self, fn: RollbackCallback) -> None:
        self._on_rollback_callbacks.add(fn)

    async def emit_connected(self) -> None:
        for fn in self._on_connected_callbacks:
            await fn()

    async def emit_disconnected(self) -> None:
        for fn in self._on_disconnected_callbacks:
            await fn()

    async def emit_rollback(self, type_: MessageType, from_level: int, to_level: int) -> None:
        for fn in self._on_rollback_callbacks:
            await fn(self, type_, from_level, to_level)


def create_datasource(config: DatasourceConfig) -> Datasource[Any]:
    from dipdup.config.abi_etherscan import EtherscanDatasourceConfig
    from dipdup.config.coinbase import CoinbaseDatasourceConfig
    from dipdup.config.evm_node import EvmNodeDatasourceConfig
    from dipdup.config.evm_subsquid import SubsquidDatasourceConfig
    from dipdup.config.http import HttpDatasourceConfig
    from dipdup.config.ipfs import IpfsDatasourceConfig
    from dipdup.config.tezos_tzkt import TzktDatasourceConfig
    from dipdup.config.tzip_metadata import TzipMetadataDatasourceConfig
    from dipdup.datasources.abi_etherscan import EtherscanDatasource
    from dipdup.datasources.coinbase import CoinbaseDatasource
    from dipdup.datasources.evm_node import EvmNodeDatasource
    from dipdup.datasources.evm_subsquid import SubsquidDatasource
    from dipdup.datasources.http import HttpDatasource
    from dipdup.datasources.ipfs import IpfsDatasource
    from dipdup.datasources.tezos_tzkt import TzktDatasource
    from dipdup.datasources.tzip_metadata import TzipMetadataDatasource

    by_config: dict[type[DatasourceConfig], type[Datasource[Any]]] = {
        EtherscanDatasourceConfig: EtherscanDatasource,
        CoinbaseDatasourceConfig: CoinbaseDatasource,
        TzktDatasourceConfig: TzktDatasource,
        TzipMetadataDatasourceConfig: TzipMetadataDatasource,
        HttpDatasourceConfig: HttpDatasource,
        IpfsDatasourceConfig: IpfsDatasource,
        SubsquidDatasourceConfig: SubsquidDatasource,
        EvmNodeDatasourceConfig: EvmNodeDatasource,
    }

    try:
        return by_config[type(config)](config)
    except KeyError as e:
        raise FrameworkException(f'Unknown datasource type: {type(config)}') from e
