from __future__ import annotations

import asyncio
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


async def readahead_by_level(
    fetcher_iter: AsyncIterator[tuple[FetcherBufferT, ...]],
    limit: int,
) -> AsyncIterator[tuple[int, tuple[FetcherBufferT, ...]]]:
    queue_name = f'fetcher_readahead:{id(fetcher_iter)}'
    queue: deque[tuple[int, tuple[FetcherBufferT, ...]]] = deque()
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


class FetcherChannel(ABC, Generic[FetcherBufferT, FetcherFilterT]):
    def __init__(
        self,
        buffer: defaultdict[Level, deque[FetcherBufferT]],
        filter: set[FetcherFilterT],
        first_level: int,
        last_level: int,
        datasource: IndexDatasource[Any],
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
        datasource: IndexDatasource[Any],
        first_level: int,
        last_level: int,
    ) -> None:
        self._datasource = datasource
        self._first_level = first_level
        self._last_level = last_level
        self._buffer: defaultdict[Level, deque[FetcherBufferT]] = defaultdict(deque)
        self._head = 0

    @abstractmethod
    def fetch_by_level(self) -> AsyncIterator[tuple[int, tuple[FetcherBufferT, ...]]]: ...
