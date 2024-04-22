from __future__ import annotations

import asyncio
import random
from abc import ABC
from abc import abstractmethod
from collections import defaultdict
from collections import deque
from contextlib import suppress
from typing import TYPE_CHECKING
from typing import Any
from typing import Generic
from typing import Protocol
from typing import TypeVar

from dipdup.performance import queues

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator
    from collections.abc import AsyncIterator

from dipdup.datasources import IndexDatasource


class HasLevel(Protocol):
    level: int

    @property
    def block_number(self) -> int:
        return self.level


Level = int
BufferT = TypeVar('BufferT', bound=HasLevel)
FilterT = TypeVar('FilterT')
DatasourceT = TypeVar('DatasourceT', bound=IndexDatasource[Any])


async def yield_by_level(
    iterable: AsyncIterator[tuple[BufferT, ...]]
) -> AsyncGenerator[tuple[Level, tuple[BufferT, ...]], None]:
    items: tuple[BufferT, ...] = ()

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


async def readahead_by_level(
    fetcher_iter: AsyncIterator[tuple[BufferT, ...]],
    limit: int,
) -> AsyncIterator[tuple[int, tuple[BufferT, ...]]]:
    queue_name = f'fetcher_readahead:{id(fetcher_iter)}'
    queue: deque[tuple[int, tuple[BufferT, ...]]] = deque()
    queues.add_queue(
        queue,
        name=queue_name,
        limit=limit,
    )
    has_more = asyncio.Event()
    need_more = asyncio.Event()

    async def _readahead() -> None:
        async for level, batch in yield_by_level(fetcher_iter):
            queue.append((level, batch))
            has_more.set()

            if len(queue) >= limit:
                need_more.clear()
                await need_more.wait()

    task = asyncio.create_task(
        _readahead(),
        name=f'fetcher:{id(fetcher_iter)}',
    )

    while True:
        while queue:
            level, batch = queue.popleft()
            need_more.set()
            yield level, batch
        has_more.clear()
        if task.done():
            await task
            break
        with suppress(asyncio.TimeoutError):
            await asyncio.wait_for(has_more.wait(), timeout=10)

    queues.remove_queue(queue_name)


class FetcherChannel(ABC, Generic[BufferT, DatasourceT, FilterT]):
    def __init__(
        self,
        buffer: defaultdict[Level, deque[BufferT]],
        filter: set[FilterT],
        first_level: int,
        last_level: int,
        datasources: tuple[DatasourceT, ...],
    ) -> None:
        super().__init__()
        self._buffer = buffer
        self._filter = filter
        self._first_level = first_level
        self._last_level = last_level
        self._datasources = datasources

        self._head: int = 0
        self._offset: int = 0

    @property
    def head(self) -> int:
        return self._head

    @property
    def fetched(self) -> bool:
        return self._head >= self._last_level

    @property
    def random_datasource(self) -> DatasourceT:
        return random.choice(self._datasources)

    @abstractmethod
    async def fetch(self) -> None:
        """Fetch a single `requets_limit` batch of items, bump channel offset"""
        ...


class DataFetcher(ABC, Generic[BufferT, DatasourceT]):
    """Fetches contract data from REST API, merges them and yields by level."""

    def __init__(
        self,
        datasources: tuple[DatasourceT, ...],
        first_level: int,
        last_level: int,
    ) -> None:
        self._datasources = datasources
        self._first_level = first_level
        self._last_level = last_level
        self._buffer: defaultdict[Level, deque[BufferT]] = defaultdict(deque)
        self._head = 0

    @property
    def random_datasource(self) -> DatasourceT:
        return random.choice(self._datasources)

    @abstractmethod
    def fetch_by_level(self) -> AsyncIterator[tuple[int, tuple[BufferT, ...]]]:
        """Iterate over events data from REST.

        Resulting data is splitted by level, deduped, sorted and ready to be processed by TezosEventsIndex.
        """
        ...
