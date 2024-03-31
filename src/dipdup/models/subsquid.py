from enum import Enum

from dipdup.models import MessageType


class SubsquidMessageType(MessageType, Enum):
    blocks = 'blocks'
    logs = 'logs'
    traces = 'traces'
    transactions = 'transactions'
