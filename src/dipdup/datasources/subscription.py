import logging
from abc import abstractmethod
from collections import defaultdict
from typing import DefaultDict, Set

from pydantic.dataclasses import dataclass
from tortoise import Optional

_logger = logging.getLogger('dipdup.datasource')


class Subscription:
    @abstractmethod
    def __hash__(self) -> int:
        ...


@dataclass
class HeadSubscription(Subscription):
    def __hash__(self) -> int:
        return hash('head')


@dataclass
class OriginationSubscription(Subscription):
    def __hash__(self) -> int:
        return hash('origination')


@dataclass
class TransactionSubscription(Subscription):
    address: Optional[str] = None

    def __hash__(self) -> int:
        return hash(f'transaction:{self.address}')


# TODO: Add `ptr` and `tags` filters
@dataclass
class BigMapSubscription(Subscription):
    address: Optional[str] = None
    path: Optional[str] = None

    def __hash__(self) -> int:
        return hash(f'big_map:{self.address}:{self.path}')


class SubscriptionManager:
    def __init__(self) -> None:
        self._subscriptions: Set[Subscription] = set()
        self._active_subscriptions: Set[Subscription] = set()
        self._initial_level: Optional[int] = None
        self._sync_levels: DefaultDict[Subscription, Optional[int]] = defaultdict(lambda: None)

    @property
    def missing_subscriptions(self) -> Set[Subscription]:
        return self._subscriptions - self._active_subscriptions

    def add(self, subscription: Subscription, log: bool = True) -> None:
        if subscription in self._subscriptions and log:
            _logger.warning(f'Subscription already exists: {subscription}')
        else:
            self._subscriptions.add(subscription)

    def remove(self, subscription: Subscription, log: bool = True) -> None:
        if subscription not in self._subscriptions and log:
            _logger.warning(f'Subscription does not exist: {subscription}')
        else:
            self._subscriptions.remove(subscription)

    def apply(self) -> None:
        self._active_subscriptions |= self._subscriptions

    def reset(self) -> None:
        self._active_subscriptions = set()
        self._sync_levels.clear()

    def set_sync_level(self, level: int, initial: bool = False) -> None:
        if initial:
            self._initial_level = level

        for subscription in self._active_subscriptions:
            if not self._sync_levels[subscription]:
                self._sync_levels[subscription] = level

    def get_sync_level(self, subscription: Subscription) -> Optional[int]:
        return self._sync_levels[subscription] or self._initial_level
