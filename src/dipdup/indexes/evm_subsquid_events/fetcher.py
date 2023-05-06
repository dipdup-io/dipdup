import asyncio
import logging
from collections import deque
from typing import AsyncGenerator

from dipdup.datasources.evm_subsquid import SubsquidDatasource
from dipdup.fetcher import DataFetcher
from dipdup.fetcher import yield_by_level
from dipdup.models.evm_subsquid import SubsquidEventData

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)


class EventLogFetcher(DataFetcher[SubsquidEventData]):
    """Fetches contract events from REST API, merges them and yields by level."""

    _datasource: SubsquidDatasource

    def __init__(
        self,
        datasource: SubsquidDatasource,
        first_level: int,
        last_level: int,
        topics: list[tuple[str | None, str]],
    ) -> None:
        self._logger = logging.getLogger('dipdup.subsquid')
        self._datasource = datasource
        self._first_level = first_level
        self._last_level = last_level
        self._topics = topics

    async def fetch_by_level(self) -> AsyncGenerator[tuple[int, tuple[SubsquidEventData, ...]], None]:
        """Iterate over events fetched fetched from REST.

        Resulting data is splitted by level, deduped, sorted and ready to be processed by TzktEventsIndex.
        """
        queue: deque[tuple[int, tuple[SubsquidEventData, ...]]] = deque()
        event_iter = self._datasource.iter_event_logs(
            self._topics,
            self._first_level,
            self._last_level,
        )

        limit = 1_000
        has_more = asyncio.Event()
        need_more = asyncio.Event()

        async def _readahead() -> None:
            async for level, batch in yield_by_level(event_iter):
                queue.append((level, batch))
                has_more.set()

                if len(queue) >= limit:
                    need_more.clear()
                    _logger.debug('%s items in queue; waiting for need_more', len(queue))
                    await need_more.wait()

        task = asyncio.create_task(_readahead())

        while True:
            while queue:
                level, batch = queue.popleft()
                need_more.set()
                yield level, batch
            has_more.clear()
            if task.done():
                await task
                break
            _logger.debug('%s items in queue; waiting for has_more', len(queue))
            await has_more.wait()
