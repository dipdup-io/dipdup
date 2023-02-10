import logging
from abc import abstractmethod
from typing import Generic
from typing import TypeVar

from dipdup.config import DatasourceConfig
from dipdup.config import IndexDatasourceConfig
from dipdup.config import ResolvedHttpConfig
from dipdup.http import HTTPGateway
from dipdup.subscriptions import Subscription
from dipdup.subscriptions import SubscriptionManager
from dipdup.utils import FormattedLogger

_logger = logging.getLogger('dipdup.datasource')


DatasourceConfigT = TypeVar('DatasourceConfigT', bound=DatasourceConfig)
IndexDatasourceConfigT = TypeVar('IndexDatasourceConfigT', bound=IndexDatasourceConfig)


class Datasource(HTTPGateway, Generic[DatasourceConfigT]):
    def __init__(self, config: DatasourceConfigT) -> None:
        self._config = config
        http_config = ResolvedHttpConfig.create(self._default_http_config, config.http)
        super().__init__(config.url, http_config)
        self._logger = _logger

    @abstractmethod
    async def run(self) -> None:
        ...

    def set_logger(self, name: str) -> None:
        self._logger = FormattedLogger(self._logger.name, name + ': {}')


class IndexDatasource(Datasource[IndexDatasourceConfigT], Generic[IndexDatasourceConfigT]):
    def __init__(
        self,
        config: IndexDatasourceConfigT,
        merge_subscriptions: bool = False,
    ) -> None:
        super().__init__(config)
        self._subscriptions: SubscriptionManager = SubscriptionManager(merge_subscriptions)

    @property
    def name(self) -> str:
        return self._http._url

    @abstractmethod
    async def subscribe(self) -> None:
        ...

    def set_sync_level(self, subscription: Subscription | None, level: int) -> None:
        self._subscriptions.set_sync_level(subscription, level)

    def get_sync_level(self, subscription: Subscription) -> int | None:
        return self._subscriptions.get_sync_level(subscription)
