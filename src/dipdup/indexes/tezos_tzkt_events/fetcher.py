from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from dipdup.fetcher import DataFetcher
from dipdup.fetcher import readahead_by_level
from dipdup.models.tezos_tzkt import TzktEventData

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from dipdup.datasources.tezos_tzkt import TzktDatasource


class EventFetcher(DataFetcher[TzktEventData]):
    """Fetches contract events from REST API, merges them and yields by level."""

    _datasource: TzktDatasource

    def __init__(
        self,
        datasource: TzktDatasource,
        first_level: int,
        last_level: int,
        event_addresses: set[str],
        event_tags: set[str],
    ) -> None:
        self._logger = logging.getLogger('dipdup.fetcher')
        self._datasource = datasource
        self._first_level = first_level
        self._last_level = last_level
        self._event_addresses = event_addresses
        self._event_tags = event_tags

    async def fetch_by_level(self) -> AsyncGenerator[tuple[int, tuple[TzktEventData, ...]], None]:
        """Iterate over events fetched fetched from REST.

        Resulting data is splitted by level, deduped, sorted and ready to be processed by TzktEventsIndex.
        """
        event_iter = self._datasource.iter_events(
            self._event_addresses,
            self._event_tags,
            self._first_level,
            self._last_level,
        )
        async for level, batch in readahead_by_level(event_iter, limit=5_000):
            yield level, batch
