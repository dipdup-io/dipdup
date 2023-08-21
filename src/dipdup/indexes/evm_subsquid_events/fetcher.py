from collections.abc import AsyncIterator

from dipdup.datasources.evm_subsquid import SubsquidDatasource
from dipdup.fetcher import DataFetcher
from dipdup.fetcher import readahead_by_level
from dipdup.models.evm_subsquid import SubsquidEventData


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
        super().__init__(datasource, first_level, last_level)
        self._topics = topics

    async def fetch_by_level(self) -> AsyncIterator[tuple[int, tuple[SubsquidEventData, ...]]]:
        """Iterate over events fetched fetched from REST.

        Resulting data is splitted by level, deduped, sorted and ready to be processed by TzktEventsIndex.
        """
        event_iter = self._datasource.iter_event_logs(
            self._topics,
            self._first_level,
            self._last_level,
        )
        async for level, batch in readahead_by_level(event_iter, limit=5_000):
            yield level, batch
