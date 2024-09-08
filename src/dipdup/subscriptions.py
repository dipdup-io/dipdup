import logging

from dipdup.exceptions import FrameworkException

_logger = logging.getLogger(__name__)


class Subscription:
    pass


class SubscriptionManager:
    def __init__(self, merge_subscriptions: bool = False) -> None:
        self._merge_subscriptions: bool = merge_subscriptions
        self._subscriptions: dict[Subscription | None, int | None] = {None: None}

    @property
    def missing_subscriptions(self) -> set[Subscription]:
        return {k for k, v in self._subscriptions.items() if k is not None and v is None}

    def add(self, subscription: Subscription) -> None:
        if subscription not in self._subscriptions:
            self._subscriptions[subscription] = None

    def remove(self, subscription: Subscription) -> None:
        if subscription not in self._subscriptions:
            _logger.warning('Subscription does not exist: %s', subscription)
        else:
            self._subscriptions.pop(subscription)

    def reset(self) -> None:
        self._subscriptions = dict.fromkeys(self._subscriptions, None)

    def set_sync_level(self, subscription: Subscription | None, level: int) -> None:
        if subscription not in self._subscriptions:
            raise FrameworkException(f'Subscription does not exist: {subscription}')

        if subscription is None:
            for sub in self._subscriptions:
                self._subscriptions[sub] = level
            return

        if self._subscriptions[subscription]:
            # NOTE: Updating sync level with merge_subscriptions=True will cause resync
            if self._merge_subscriptions:
                return
            _logger.debug('%s sync level updated: %s -> %s', subscription, self._subscriptions[subscription], level)

        self._subscriptions[subscription] = level

    def get_sync_level(self, subscription: Subscription) -> int | None:
        if subscription not in self._subscriptions:
            raise FrameworkException(f'Subscription does not exist: {subscription}')
        return self._subscriptions[subscription] or self._subscriptions[None]
