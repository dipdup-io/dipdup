import logging
from collections import deque
from contextlib import AsyncExitStack
from contextlib import contextmanager
from typing import AsyncGenerator
from typing import Deque
from typing import Iterator
from typing import Tuple
from unittest.mock import patch

from dipdup.config import DipDupConfig
from dipdup.config import SqliteDatabaseConfig
from dipdup.datasources.tzkt.datasource import OperationFetcher
from dipdup.dipdup import DipDup
from dipdup.index import OperationIndex
from dipdup.index import OperationSubgroup
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
    async def _process_level_operations(self, operation_subgroups: Tuple[OperationSubgroup, ...]) -> None:
        for operation_subgroup in operation_subgroups:
            await self._match_operation_subgroup(operation_subgroup)


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


async def create_test_dipdup(config: DipDupConfig, stack: AsyncExitStack) -> DipDup:
    config.database = SqliteDatabaseConfig(kind='sqlite', path=':memory:')
    config.initialize(skip_imports=True)

    dipdup = DipDup(config)
    await dipdup._create_datasources()
    await dipdup._set_up_database(stack)
    await dipdup._set_up_hooks()
    await dipdup._initialize_schema()
    return dipdup
