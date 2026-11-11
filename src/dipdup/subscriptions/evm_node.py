from abc import ABC
from typing import Any
from typing import Literal

from pydantic.dataclasses import dataclass

from dipdup.subscriptions import Subscription


class EvmNodeSubscription(ABC, Subscription):
    name: str

    def get_params(self) -> list[Any]:
        return [self.name]


@dataclass(frozen=True)
class EvmNodeHeadSubscription(EvmNodeSubscription):
    name: Literal['newHeads'] = 'newHeads'
    transactions: bool = False


@dataclass(frozen=True)
class EvmNodeLogsSubscription(EvmNodeSubscription):
    name: Literal['logs'] = 'logs'
    address: str | tuple[str, ...] | None = None
    topics: tuple[tuple[str, ...], ...] | None = None

    def get_params(self) -> list[Any]:
        # NOTE: omit unset keys instead of emitting `null`; strict nodes (Octez/Etherlink EVM) reject `null`
        filters: dict[str, Any] = {}
        if self.address is not None:
            filters['address'] = self.address
        if self.topics is not None:
            filters['topics'] = self.topics
        return [*super().get_params(), filters]


@dataclass(frozen=True)
class EvmNodeSyncingSubscription(EvmNodeSubscription):
    name: Literal['syncing'] = 'syncing'
