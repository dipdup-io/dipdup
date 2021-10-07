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


class ReindexingReason(Enum):
    MANUAL = 'triggered manually from callback'
    MIGRATION = 'applied migration requires reindexing'
    CLI_OPTION = 'run with `--reindex` option'
    ROLLBACK = 'reorg message received and can\'t be processed'
    CONFIG_HASH_MISMATCH = 'index config has been modified'
    SCHEMA_HASH_MISMATCH = 'database schema has been modified'
    BLOCK_HASH_MISMATCH = 'block hash mismatch, missed rollback when DipDup was stopped'
    MISSING_INDEX_TEMPLATE = 'index template is missing, can\'t restore index state'
