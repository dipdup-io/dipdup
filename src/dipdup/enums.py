from enum import Enum


class MessageType(Enum):
    operation = 'operation'
    big_map = 'big_map'
    head = 'head'


class IndexType(Enum):
    operation = 'operation'
    big_map = 'big_map'


class IndexStatus(Enum):
    NEW = 'NEW'
    SYNCING = 'SYNCING'
    REALTIME = 'REALTIME'
    ROLLBACK = 'ROLLBACK'
    ONESHOT = 'ONESHOT'
