from enum import Enum
from typing import Dict


class ReversedEnum(Enum):
    ...


class MessageType(Enum):
    operation = 'operation'
    big_map = 'big_map'
    head = 'head'


class IndexType(Enum):
    operation = 'operation'
    big_map = 'big_map'
    head = 'head'


class IndexStatus(Enum):
    NEW = 'NEW'
    SYNCING = 'SYNCING'
    REALTIME = 'REALTIME'
    ROLLBACK = 'ROLLBACK'
    ONESHOT = 'ONESHOT'


class ReindexingReason(ReversedEnum):
    MANUAL = 'triggered manually from callback'
    MIGRATION = 'applied migration requires reindexing'
    ROLLBACK = 'reorg message received and can\'t be processed'
    CONFIG_HASH_MISMATCH = 'index config has been modified'
    SCHEMA_HASH_MISMATCH = 'database schema has been modified'
    BLOCK_HASH_MISMATCH = 'block hash mismatch, missed rollback when DipDup was stopped'
    MISSING_INDEX_TEMPLATE = 'index template is missing, can\'t restore index state'


class ReindexingReasonC(Enum):
    manual = 'manual'
    migration = 'migration'
    rollback = 'rollback'
    config_modified = 'config_modified'
    schema_modified = 'schema_modified'


class ReindexingAction(ReversedEnum):
    exception = 'exception'
    wipe = 'wipe'
    ignore = 'ignore'


reason_to_reasonc: Dict[ReindexingReason, ReindexingReasonC] = {
    ReindexingReason.MANUAL: ReindexingReasonC.manual,
    ReindexingReason.MIGRATION: ReindexingReasonC.migration,
    ReindexingReason.ROLLBACK: ReindexingReasonC.rollback,
    ReindexingReason.CONFIG_HASH_MISMATCH: ReindexingReasonC.config_modified,
    ReindexingReason.SCHEMA_HASH_MISMATCH: ReindexingReasonC.schema_modified,
    ReindexingReason.BLOCK_HASH_MISMATCH: ReindexingReasonC.rollback,
    ReindexingReason.MISSING_INDEX_TEMPLATE: ReindexingReasonC.config_modified,
}

reasonc_to_reason: Dict[ReindexingReasonC, ReindexingReason] = {
    ReindexingReasonC.manual: ReindexingReason.MANUAL,
    ReindexingReasonC.migration: ReindexingReason.MIGRATION,
    ReindexingReasonC.rollback: ReindexingReason.ROLLBACK,
    ReindexingReasonC.config_modified: ReindexingReason.CONFIG_HASH_MISMATCH,
    ReindexingReasonC.schema_modified: ReindexingReason.SCHEMA_HASH_MISMATCH,
}
