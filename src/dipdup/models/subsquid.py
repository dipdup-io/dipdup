from enum import Enum
from typing import NotRequired
from typing import TypedDict

from dipdup.models import MessageType


class SubsquidMessageType(MessageType, Enum):
    blocks = 'blocks'
    logs = 'logs'
    traces = 'traces'
    transactions = 'transactions'


FieldSelection = dict[str, dict[str, bool]]


class AbstractSubsquidQuery(TypedDict):
    fromBlock: int
    toBlock: NotRequired[int]
    includeAllBlocks: NotRequired[bool]
