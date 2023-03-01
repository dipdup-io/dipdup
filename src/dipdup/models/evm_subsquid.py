from enum import Enum
from typing import Any
from typing import Generic
from typing import TypeVar

from pydantic.dataclasses import dataclass

PayloadT = TypeVar('PayloadT', bound=Any)


class SubsquidMessageType(Enum):
    """Enum for filenames in squid archives"""

    blocks = 'blocks.arrow_stream'
    logs = 'logs.arrow_stream'


class SubsquidEvent(Generic[PayloadT]):
    ...


class SubsquidOperation:
    ...


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
    # FIXME: temporary for HasLevel
    level: int
