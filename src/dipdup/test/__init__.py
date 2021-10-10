import logging
from collections import deque
from contextlib import contextmanager
from typing import AsyncGenerator, Deque, Iterator, Tuple
from unittest.mock import patch

from dipdup.datasources.tzkt.datasource import OperationFetcher
from dipdup.index import OperationIndex
from dipdup.models import OperationData

logging.basicConfig(level=logging.ERROR)


# NOTE: Not an actual fuzzer :)
class OperationFetcherFuzzer(OperationFetcher):
    """This thing is lazy, so instead of fetching all operations it returns the same data over and over again."""

    levels: int
    repeats: int

    def __new__(cls, *a, **kw):
        super().__new__(cls, *a, **kw)
        cls.levels = 100
        cls.repeats = 100

    async def fetch_operations_by_level(self) -> AsyncGenerator[Tuple[int, Tuple[OperationData, ...]], None]:
        self._datasource._http._config.batch_size = 1000
        level_operations: Deque[Tuple[int, Tuple[OperationData, ...]]] = deque()
        async for level, operations in super().fetch_operations_by_level():
            level_operations.append((level, operations))
            if len(level_operations) >= self.levels:
                break

        for _ in range(self.repeats):
            for level, operations in level_operations:
                yield level, operations


class OperationIndexFuzzer(OperationIndex):
    async def _process_level_operations(self, operations: Tuple[OperationData, ...]) -> None:
        await self._match_operations(operations)


@contextmanager
def with_operation_fetcher_fuzzer(levels=100, repeats=100) -> Iterator[None]:
    OperationFetcherFuzzer.levels = levels
    OperationFetcherFuzzer.repeats = repeats
    with patch('dipdup.datasources.tzkt.datasource.OperationFetcher', OperationFetcherFuzzer):
        yield


@contextmanager
def with_operation_index_fuzzer(levels=100, repeats=100) -> Iterator[None]:
    with with_operation_fetcher_fuzzer(levels=levels, repeats=repeats):
        with patch('dipdup.index.OperationIndex', OperationIndexFuzzer):
            yield
