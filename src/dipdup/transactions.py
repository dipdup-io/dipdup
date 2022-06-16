import asyncio
from contextlib import asynccontextmanager
from contextlib import contextmanager
from typing import AsyncIterator
from typing import Generator
from typing import Optional

from tortoise.transactions import in_transaction

import dipdup.models
from dipdup.utils.database import get_connection
from dipdup.utils.database import set_connection


class TransactionManager:
    def __init__(self, depth: int = 2, cleanup_interval: int = 60) -> None:
        self._depth = depth
        self._cleanup_interval = cleanup_interval
        self._transaction_level: Optional[int] = None

    @contextmanager
    def register(self) -> Generator[None, None, None]:
        fn = dipdup.models.get_transaction_level
        try:
            fn()
        except RuntimeError:
            pass
        else:
            raise RuntimeError('TransactionManager is already registered')

        dipdup.models.get_transaction_level = lambda: self._transaction_level
        yield
        dipdup.models.get_transaction_level = fn

    @asynccontextmanager
    async def in_transaction(
        self,
        level: Optional[int] = None,
        sync_level: Optional[int] = None,
    ) -> AsyncIterator[None]:
        """Enforce using transaction for all queries inside wrapped block. Works for a single DB only."""
        try:
            original_conn = get_connection()
            async with in_transaction() as conn:
                set_connection(conn)

                if self._transaction_level:
                    raise ValueError('Transaction is already started')

                if level and self._depth:
                    if not sync_level or sync_level - level <= self._depth:
                        self._transaction_level = level

                yield
        finally:
            set_connection(original_conn)
            self._transaction_level = None

    async def cleanup_task(self, event: asyncio.Event, interval: int) -> None:
        """Cleanup outdated model updates"""
        await event.wait()

        while True:
            await asyncio.sleep(interval)
            last_index = await dipdup.models.Index.filter().order_by('level').first()
            if not last_index:
                raise RuntimeError('No indexes found')

            level = last_index.level - self._depth
            await dipdup.models.ModelUpdate.filter(level__lt=level).delete()
            await asyncio.sleep(interval)
