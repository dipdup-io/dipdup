from enum import Enum
from typing import Any
from typing import Generic
from typing import Literal
from typing import TypeVar

from pydantic import BaseModel
from pydantic.dataclasses import dataclass

from dipdup.subscriptions import Subscription

PayloadT = TypeVar('PayloadT', bound=BaseModel)


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
    # transaction_hash: str
    # transaction_index: int
    # FIXME: temporary field for HasLevel protocol, set somewhere
    level: int


@dataclass
class SubsquidEvent(Generic[PayloadT]):
    data: SubsquidEventData
    payload: PayloadT


class SubsquidOperation:
    ...


@dataclass(frozen=True)
class EventLogSubscription(Subscription):
    type: Literal['event_log'] = 'event_log'
    method = ''

    def get_request(self) -> list[dict[str, Any]]:
        return []
