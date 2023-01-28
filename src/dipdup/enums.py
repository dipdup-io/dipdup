from enum import Enum

from dipdup import env


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


# TODO: Remove in 7.0
if env.NEXT:

    class IndexType(Enum):
        """Enum for `dipdup.models.Index`"""

        operation = 'operation'
        operation_unfiltered = 'operation_unfiltered'
        big_map = 'big_map'
        head = 'head'
        token_transfer = 'token_transfer'
        event = 'event'

else:

    class IndexType(Enum):  # type: ignore[no-redef]
        """Enum for `dipdup.models.Index`"""

        operation = 'operation'
        big_map = 'big_map'
        head = 'head'
        token_transfer = 'token_transfer'
        event = 'event'


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
