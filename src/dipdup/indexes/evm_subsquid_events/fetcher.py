import logging
from typing import AsyncGenerator

from dipdup.datasources.evm_subsquid import SubsquidDatasource
from dipdup.fetcher import DataFetcher
from dipdup.fetcher import yield_by_level
from dipdup.models.evm_subsquid import SubsquidEventData


class EventLogFetcher(DataFetcher[SubsquidEventData]):
    """Fetches contract events from REST API, merges them and yields by level."""

    _datasource: SubsquidDatasource

    def __init__(
        self,
        datasource: SubsquidDatasource,
        first_level: int,
        last_level: int,
        addresses: set[str],
        topics: set[str],
    ) -> None:
        self._logger = logging.getLogger('dipdup.subsquid')
        self._datasource = datasource
        self._first_level = first_level
        self._last_level = last_level
        self._addresses = addresses
        self._topics = topics

    async def fetch_by_level(self) -> AsyncGenerator[tuple[int, tuple[SubsquidEventData, ...]], None]:
        """Iterate over events fetched fetched from REST.

        Resulting data is splitted by level, deduped, sorted and ready to be processed by TzktEventsIndex.
        """
        event_iter = self._datasource.iter_event_logs(
            self._addresses,
            self._topics,
            self._first_level,
            self._last_level,
        )
        async for level, batch in yield_by_level(event_iter):
            yield level, batch
