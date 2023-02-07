import logging
from abc import abstractmethod

from dipdup.config import HttpConfig
from dipdup.config import ResolvedHttpConfig
from dipdup.http import HTTPGateway
from dipdup.subscriptions import Subscription
from dipdup.subscriptions import SubscriptionManager
from dipdup.utils import FormattedLogger

_logger = logging.getLogger('dipdup.datasource')


class Datasource(HTTPGateway):
    def __init__(self, url: str, http_config: HttpConfig | None = None) -> None:
        config = ResolvedHttpConfig.create(self._default_http_config, http_config)
        super().__init__(url, config)
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
    def __init__(
        self,
        url: str,
        http_config: HttpConfig | None = None,
        merge_subscriptions: bool = False,
    ) -> None:
        super().__init__(url, http_config)
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
