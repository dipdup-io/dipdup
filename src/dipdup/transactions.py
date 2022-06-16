from contextlib import asynccontextmanager
from functools import wraps
from typing import AsyncIterator
from typing import Optional
from typing import Set
from typing import Type

from tortoise.transactions import in_transaction

from dipdup.models import Model
from dipdup.utils.database import get_connection
from dipdup.utils.database import set_connection


class TransactionManager:
    def __init__(self, history_depth: int = 2) -> None:
        self._history_depth = history_depth
        self._transaction_level: Optional[int] = None
        self._models: Set[Model] = set()

    def register_model(self, model: Type[Model]) -> None:
        if model in self._models:
            raise ValueError(f'Model `{model}` is already registered')

        model.save = self._wrapper(model.save)  # type: ignore
        model.delete = self._wrapper(model.delete)  # type: ignore

    def _wrapper(self, fn):
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            kwargs['_level'] = self._transaction_level
            return await fn(*args, **kwargs)

        return wrapper

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

                if level and (not sync_level or sync_level - level <= self._history_depth):
                    self._transaction_level = level

                yield
        finally:
            set_connection(original_conn)
            self._transaction_level = None
