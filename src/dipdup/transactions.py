from collections import deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from tortoise.transactions import in_transaction

import dipdup.models
from dipdup.database import get_connection
from dipdup.database import set_connection


class TransactionManager:
    """Manages versioned transactions"""

    def __init__(
        self,
        depth: int | None = None,
        immune_tables: set[str] | None = None,
    ) -> None:
        self._depth = depth
        self._immune_tables = immune_tables or set()
        self._transaction: dipdup.models.VersionedTransaction | None = None
        self._pending_updates: deque[dipdup.models.ModelUpdate] = deque()

    @asynccontextmanager
    async def register(self) -> AsyncIterator[None]:
        """Register this manager to use in the current scope"""
        original_get_transaction = dipdup.models.get_transaction
        original_get_pending_updates = dipdup.models.get_pending_updates

        dipdup.models.get_transaction = lambda: self._transaction
        dipdup.models.get_pending_updates = lambda: self._pending_updates
        yield
        dipdup.models.get_transaction = original_get_transaction
        dipdup.models.get_pending_updates = original_get_pending_updates

    @asynccontextmanager
    async def in_transaction(
        self,
        level: int | None = None,
        sync_level: int | None = None,
        index: str | None = None,
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

                if self._transaction:
                    await self._commit()
        finally:
            self._transaction = None
            set_connection(original_conn)

    async def _commit(self) -> None:
        """Save pending updates to DB in the same order as they were added"""
        while self._pending_updates:
            await self._pending_updates.popleft().save()

    async def cleanup(self) -> None:
        """Cleanup outdated model updates"""
        if not self._depth:
            return
        most_recent_index = await dipdup.models.Index.filter().order_by('-level').first()
        if not most_recent_index:
            return

        last_level = most_recent_index.level - self._depth
        await dipdup.models.ModelUpdate.filter(level__lt=last_level).delete()
