from enum import Enum
from typing import Any
from typing import Generic
from typing import Literal
from typing import TypeVar

from pydantic import BaseModel
from pydantic.dataclasses import dataclass

from dipdup.subscriptions import Subscription

PayloadT = TypeVar('PayloadT', bound=BaseModel)


# FIXME: Outdated values
class SubsquidMessageType(Enum):
    """Enum for filenames in squid archives"""

    blocks = 'blocks.arrow_stream'
    logs = 'logs.arrow_stream'


@dataclass(frozen=True)
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
    method = ''

    def get_request(self) -> list[dict[str, Any]]:
        return []
