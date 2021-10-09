from enum import Enum


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
