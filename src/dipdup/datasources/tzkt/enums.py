from enum import Enum


class TzktMessageType(Enum):
    STATE = 0
    DATA = 1
    REORG = 2
