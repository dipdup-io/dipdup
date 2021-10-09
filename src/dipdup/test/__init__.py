from collections import deque
from contextlib import contextmanager
from typing import AsyncGenerator, Deque, Iterator, Tuple
from unittest.mock import patch

from dipdup.datasources.tzkt.datasource import OperationFetcher
from dipdup.models import OperationData


class LazyOperationFetcher(OperationFetcher):
    """This thing is lazy, so instead of fetching all operations it returns the same data over and over again."""

    def __new__(cls):
        super().__new__()
        cls.levels = 100
        cls.repeats = 100

    @contextmanager
    @classmethod
    def patch(cls, levels=100, repeats=100) -> Iterator[None]:
        cls.levels = levels
        cls.repeats = repeats
        with patch('dipdup.datasources.tzkt.datasource.OperationFetcher', cls):
            yield

    async def fetch_operations_by_level(self) -> AsyncGenerator[Tuple[int, Tuple[OperationData, ...]], None]:
        level_operations: Deque[Tuple[int, Tuple[OperationData, ...]]] = deque()
        async for level, operations in super().fetch_operations_by_level():
            level_operations.append((level, operations))
            if len(level_operations) >= self.levels:
                break

        for _ in range(self.repeats):
            for level, operations in level_operations:
                yield level, operations
