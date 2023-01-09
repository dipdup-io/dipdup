from __future__ import annotations

import logging
from typing import AsyncGenerator

from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.fetcher import DataFetcher
from dipdup.fetcher import yield_by_level
from dipdup.models import EventData


class EventFetcher(DataFetcher[EventData]):
    """Fetches contract events from REST API, merges them and yields by level."""

    def __init__(
        self,
        datasource: 'TzktDatasource',
        first_level: int,
        last_level: int,
        event_addresses: set[str],
        event_tags: set[str],
    ) -> None:
        self._logger = logging.getLogger('dipdup.tzkt')
        self._datasource = datasource
        self._first_level = first_level
        self._last_level = last_level
        self._event_addresses = event_addresses
        self._event_tags = event_tags

    async def fetch_by_level(self) -> AsyncGenerator[tuple[int, tuple[EventData, ...]], None]:
        """Iterate over events fetched fetched from REST.

        Resulting data is splitted by level, deduped, sorted and ready to be processed by EventIndex.
        """
        event_iter = self._datasource.iter_events(
            self._event_addresses,
            self._event_tags,
            self._first_level,
            self._last_level,
        )
        async for level, batch in yield_by_level(event_iter):
            yield level, batch
