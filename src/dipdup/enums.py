from enum import Enum


class MessageType(Enum):
    operation = 'operation'
    big_map = 'big_map'
    head = 'head'


class IndexType(Enum):
    operation = 'operation'
    big_map = 'big_map'
    head = 'head'


class OperationType(Enum):
    transaction = 'transaction'
    origination = 'origination'
    migration = 'migration'


class SkipHistory(Enum):
    never = 'never'
    once = 'once'
    always = 'always'


class IndexStatus(Enum):
    NEW = 'NEW'
    SYNCING = 'SYNCING'
    REALTIME = 'REALTIME'
    ROLLBACK = 'ROLLBACK'
    # TODO: Rename to DISABLED or something one day
    ONESHOT = 'ONESHOT'


# NOTE: Used as a key in config, must inherit from str
class ReindexingReason(str, Enum):
    manual = 'manual'
    migration = 'migration'
    rollback = 'rollback'
    config_modified = 'config_modified'
    schema_modified = 'schema_modified'


class ReindexingAction(Enum):
    exception = 'exception'
    wipe = 'wipe'
    ignore = 'ignore'
