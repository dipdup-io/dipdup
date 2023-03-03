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
    block_number: int
    log_index: int
    transaction_index: int
    topic0: str
    topic1: str | None
    topic2: str | None
    topic3: str | None
    data: str
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
