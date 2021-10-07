from enum import Enum


class TzktMessageType(Enum):
    STATE = 0
    DATA = 1
    REORG = 2


OPERATION_FIELDS = (
    "type",
    "id",
    "level",
    "timestamp",
    "hash",
    "counter",
    "sender",
    "nonce",
    "target",
    "initiator",
    "amount",
    "storage",
    "status",
    "hasInternals",
    "diffs",
)
ORIGINATION_MIGRATION_FIELDS = (
    "id",
    "level",
    "timestamp",
    "storage",
    "diffs",
    "account",
    "balanceChange",
)
ORIGINATION_OPERATION_FIELDS = (
    *OPERATION_FIELDS,
    "originatedContract",
)
TRANSACTION_OPERATION_FIELDS = (
    *OPERATION_FIELDS,
    "parameter",
    "hasInternals",
)


class OperationFetcherRequest(Enum):
    """Represents multiple TzKT calls to be merged into a single batch of operations"""

    sender_transactions = 'sender_transactions'
    target_transactions = 'target_transactions'
    originations = 'originations'
