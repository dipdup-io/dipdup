from enum import Enum


class LoggingValues(Enum):
    """Enum for `logging` field values."""

    default = 'default'
    quiet = 'quiet'
    verbose = 'verbose'


class MessageType(Enum):
    """Enum for realtime message types"""

    operation = 'operation'
    big_map = 'big_map'
    head = 'head'
    token_transfer = 'token_transfer'
    event = 'event'


class IndexType(Enum):
    """Enum for `dipdup.models.Index`"""

    tezos_tzkt_operations = 'tezos.tzkt.operations'
    tezos_tzkt_operations_unfiltered = 'tezos.tzkt.operations_unfiltered'
    tezos_tzkt_big_maps = 'tezos.tzkt.big_maps'
    tezos_tzkt_head = 'tezos.tzkt.head'
    tezos_tzkt_token_transfers = 'tezos.tzkt.token_transfers'
    tezos_tzkt_events = 'tezos.tzkt.events'
    evm_subsquid_operations = 'evm.subsquid.operations'
    evm_subsquid_events = 'evm.subsquid.events'


class OperationType(Enum):
    """Type of blockchain operation"""

    transaction = 'transaction'
    origination = 'origination'
    migration = 'migration'


class SkipHistory(Enum):
    """Whether to skip indexing operation history and use only current state"""

    never = 'never'
    once = 'once'
    always = 'always'


class IndexStatus(Enum):
    NEW = 'NEW'
    SYNCING = 'SYNCING'
    REALTIME = 'REALTIME'
    # TODO: Remove in 7.0
    ROLLBACK = 'ROLLBACK'
    # TODO: Rename to DISABLED or something one day
    ONESHOT = 'ONESHOT'


# NOTE: Used as a key in config, must inherit from str
class ReindexingReason(str, Enum):
    """Reason that caused reindexing"""

    manual = 'manual'
    migration = 'migration'
    rollback = 'rollback'
    config_modified = 'config_modified'
    schema_modified = 'schema_modified'


class ReindexingAction(Enum):
    """Action that should be performed on reindexing"""

    exception = 'exception'
    wipe = 'wipe'
    ignore = 'ignore'


class TokenStandard(Enum):
    FA12 = 'fa1.2'
    FA2 = 'fa2'
