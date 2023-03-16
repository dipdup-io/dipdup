# from abc import ABC
import logging
from abc import ABC
from enum import Enum
from typing import Any
from typing import Generic
from typing import Literal
from typing import TypeVar

from pydantic import BaseModel
from pydantic.dataclasses import dataclass

from dipdup.subscriptions import Subscription

PayloadT = TypeVar('PayloadT', bound=BaseModel)


logging.getLogger('pysignalr').setLevel(logging.DEBUG)
logging.getLogger('websockets').setLevel(logging.DEBUG)


# FIXME: Outdated values
class SubsquidMessageType(Enum):
    """Enum for filenames in squid archives"""

    blocks = 'blocks.arrow_stream'
    logs = 'logs.arrow_stream'


@dataclass
class SubsquidEventData:
    address: str
    # block_hash: str
    # block_number: int
    data: str
    # index: int
    # removed: bool
    topics: tuple[str, ...]
    # TODO: Either hash or id required for merging logs into txs (for operation index)
    # transaction_hash: str
    # transaction_index: int
    level: int

    @classmethod
    def from_json(
        cls,
        event_json: dict[str, Any],
    ) -> 'SubsquidEventData':
        return SubsquidEventData(
            address=event_json['address'],
            data=event_json['data'],
            topics=tuple(event_json['topics']),
            level=event_json['blockNumber'],
        )

    @property
    def block_number(self) -> int:
        return self.level


@dataclass
class SubsquidEvent(Generic[PayloadT]):
    data: SubsquidEventData
    payload: PayloadT


class SubsquidOperation:
    ...


@dataclass(frozen=True)
class ArchiveSubscription(Subscription):
    type: Literal['archive'] = 'archive'


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
