from contextlib import asynccontextmanager
from contextlib import contextmanager
from typing import AsyncIterator
from typing import Generator
from typing import Optional
from typing import Set

from tortoise.transactions import in_transaction

import dipdup.models
from dipdup.utils.database import get_connection
from dipdup.utils.database import set_connection


class TransactionManager:
    def __init__(
        self,
        depth: int = 2,
        immune_tables: Optional[Set[str]] = None,
    ) -> None:
        self._depth = depth
        self._immune_tables = immune_tables or set()
        self._transaction: Optional[dipdup.models.VersionedTransaction] = None

    @contextmanager
    def register(self) -> Generator[None, None, None]:
        original_get_transaction = dipdup.models.get_transaction
        try:
            original_get_transaction()
        except RuntimeError:
            pass
        else:
            raise RuntimeError('TransactionManager is already registered')

        dipdup.models.get_transaction = lambda: self._transaction
        yield
        dipdup.models.get_transaction = original_get_transaction

    @asynccontextmanager
    async def in_transaction(
        self,
        level: Optional[int] = None,
        sync_level: Optional[int] = None,
        index: Optional[str] = None,
    ) -> AsyncIterator[None]:
        """Enforce using transaction for all queries inside wrapped block. Works for a single DB only."""
        try:
            original_conn = get_connection()
            async with in_transaction() as conn:
                set_connection(conn)

                if self._transaction:
                    raise ValueError('Transaction is already started')

                if level and index and self._depth:
                    if not sync_level or sync_level - level <= self._depth:
                        self._transaction = dipdup.models.VersionedTransaction(
                            level,
                            index,
                            self._immune_tables,
                        )

                yield
        finally:
            self._transaction = None
            set_connection(original_conn)

    async def cleanup(self, last_level: int) -> None:
        """Cleanup outdated model updates"""
        await dipdup.models.ModelUpdate.filter(level__lt=last_level).delete()
