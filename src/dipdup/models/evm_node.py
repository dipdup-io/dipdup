# from abc import ABC
from abc import ABC
from typing import Any
from typing import Literal

from pydantic.dataclasses import dataclass

from dipdup.subscriptions import Subscription


class NodeSubscription(ABC, Subscription):
    name: str

    def get_params(self) -> list[Any]:
        return [self.name]


@dataclass(frozen=True)
class NodeHeadSubscription(NodeSubscription):
    name: Literal['newHeads'] = 'newHeads'


@dataclass(frozen=True)
class NodeLogsSubscription(NodeSubscription):
    name: Literal['logs'] = 'logs'
    address: str | tuple[str, ...] | None = None
    topics: tuple[tuple[str, ...], ...] | None = None

    def get_params(self) -> list[Any]:
        return super().get_params() + [
            {
                'address': self.address,
                'topics': self.topics,
            }
        ]


@dataclass(frozen=True)
class NodeSyncSubscription(NodeSubscription):
    name: Literal['syncing'] = 'syncing'
