from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from collections import defaultdict
from collections import deque
from typing import AsyncGenerator
from typing import AsyncIterator
from typing import Generic
from typing import Protocol
from typing import TypeVar

from dipdup.datasources.tzkt.datasource import TzktDatasource


class HasLevel(Protocol):
    level: int


Level = int
FetcherBufferT = TypeVar('FetcherBufferT', bound=HasLevel)
FetcherFilterT = TypeVar('FetcherFilterT')


async def yield_by_level(
    iterable: AsyncIterator[tuple[FetcherBufferT, ...]]
) -> AsyncGenerator[tuple[Level, tuple[FetcherBufferT, ...]], None]:
    items: tuple[FetcherBufferT, ...] = ()

    async for item_batch in iterable:
        items = items + item_batch

        # NOTE: Yield slices by level except the last one
        while True:
            for i in range(len(items) - 1):
                curr_level, next_level = items[i].level, items[i + 1].level

                # NOTE: Level boundaries found. Exit for loop, stay in while.
                if curr_level != next_level:
                    yield curr_level, items[: i + 1]
                    items = items[i + 1 :]
                    break
            else:
                break

    if items:
        yield items[0].level, items


class FetcherChannel(ABC, Generic[FetcherBufferT, FetcherFilterT]):
    def __init__(
        self,
        buffer: defaultdict[Level, deque[FetcherBufferT]],
        filter: set[FetcherFilterT],
        first_level: int,
        last_level: int,
        datasource: 'TzktDatasource',
    ) -> None:
        super().__init__()
        self._buffer = buffer
        self._filter = filter
        self._first_level = first_level
        self._last_level = last_level
        self._datasource = datasource

        self._head: int = 0
        self._offset: int = 0

    @property
    def head(self) -> int:
        return self._head

    @property
    def fetched(self) -> bool:
        return self._head >= self._last_level

    @abstractmethod
    async def fetch(self) -> None:
        """Fetch a single `requets_limit` batch of items, bump channel offset"""
        ...


class DataFetcher(ABC, Generic[FetcherBufferT]):
    def __init__(
        self,
        datasource: 'TzktDatasource',
        first_level: int,
        last_level: int,
    ) -> None:
        self._datasource = datasource
        self._first_level = first_level
        self._last_level = last_level
        self._buffer: defaultdict[Level, deque[FetcherBufferT]] = defaultdict(deque)
        self._head = 0

    @abstractmethod
    def fetch_by_level(self) -> AsyncIterator[tuple[int, tuple[FetcherBufferT, ...]]]:
        ...
