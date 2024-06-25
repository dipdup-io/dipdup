from collections.abc import AsyncIterator

from dipdup.datasources.starknet_subsquid import StarknetSubsquidDatasource
from dipdup.fetcher import readahead_by_level
from dipdup.indexes.starknet_subsquid import StarknetSubsquidFetcher
from dipdup.models.starknet import StarknetEventData
from dipdup.models.starknet_subsquid import EventRequest

STARKNET_SUBSQUID_READAHEAD_LIMIT = 10000


class StarknetSubsquidEventFetcher(StarknetSubsquidFetcher[StarknetEventData]):
    def __init__(
        self,
        datasources: tuple[StarknetSubsquidDatasource, ...],
        first_level: int,
        last_level: int,
        event_ids: dict[str, set[str]],
    ) -> None:
        super().__init__(datasources, first_level, last_level)
        self._event_ids = event_ids

    async def fetch_by_level(self) -> AsyncIterator[tuple[int, tuple[StarknetEventData, ...]]]:
        filters: tuple[EventRequest, ...] = tuple(
            {
                'key0': list(ids),
                'fromAddress': [address],
            }
            for address, ids in self._event_ids.items()
        )
        event_iter = self.random_datasource.iter_events(
            first_level=self._first_level,
            last_level=self._last_level,
            filters=filters,
        )
        async for level, batch in readahead_by_level(event_iter, limit=STARKNET_SUBSQUID_READAHEAD_LIMIT):
            yield level, batch
