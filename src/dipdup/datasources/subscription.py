import logging
from abc import abstractmethod
from typing import Any
from typing import Dict
from typing import Optional
from typing import Set

from dipdup.exceptions import FrameworkException

_logger = logging.getLogger('dipdup.datasource')


class Subscription:
    type: str
    method: str

    @abstractmethod
    def get_request(self) -> Any:
        ...


class SubscriptionManager:
    def __init__(self, merge_subscriptions: bool = False) -> None:
        self._merge_subscriptions: bool = merge_subscriptions
        self._subscriptions: Dict[Optional[Subscription], Optional[int]] = {None: None}

    @property
    def missing_subscriptions(self) -> Set[Subscription]:
        return {k for k, v in self._subscriptions.items() if k is not None and v is None}

    def add(self, subscription: Subscription) -> None:
        if subscription not in self._subscriptions:
            self._subscriptions[subscription] = None

    def remove(self, subscription: Subscription) -> None:
        if subscription not in self._subscriptions:
            _logger.warning(f'Subscription does not exist: {subscription}')
        else:
            self._subscriptions.pop(subscription)

    def reset(self) -> None:
        self._subscriptions = dict.fromkeys(self._subscriptions, None)

    def set_sync_level(self, subscription: Optional[Subscription], level: int) -> None:
        if subscription not in self._subscriptions:
            raise FrameworkException(f'Subscription does not exist: {subscription}')

        if self._subscriptions[subscription]:
            # NOTE: Updating sync level with merge_subscriptions=True will cause resync
            if self._merge_subscriptions:
                return
            _logger.warning('%s sync level updated: %s -> %s', subscription, self._subscriptions[subscription], level)

        self._subscriptions[subscription] = level

    def get_sync_level(self, subscription: Subscription) -> Optional[int]:
        if subscription not in self._subscriptions:
            raise FrameworkException(f'Subscription does not exist: {subscription}')
        return self._subscriptions[subscription] or self._subscriptions[None]
