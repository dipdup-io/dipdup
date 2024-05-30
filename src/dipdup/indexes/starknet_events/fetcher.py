from collections.abc import AsyncIterator

from dipdup.datasources.starknet_subsquid import StarknetSubsquidDatasource
from dipdup.fetcher import readahead_by_level
from dipdup.indexes.starknet_subsquid import StarknetSubsquidFetcher
from dipdup.models.starknet import StarknetEventData

STARKNET_SUBSQUID_READAHEAD_LIMIT = 10000


class StarknetSubsquidEventFetcher(StarknetSubsquidFetcher[StarknetEventData]):
    def __init__(
        self,
        datasources: tuple[StarknetSubsquidDatasource, ...],
        first_level: int,
        last_level: int,
        event_ids: list[str],
    ) -> None:
        super().__init__(datasources, first_level, last_level)
        self._event_ids = event_ids

    async def fetch_by_level(self) -> AsyncIterator[tuple[int, tuple[StarknetEventData, ...]]]:
        # TODO: probably add from_address filter on this level?
        # key0 contains the event identifier
        event_iter = self.random_datasource.iter_events(
            self._first_level,
            self._last_level,
            ({'key0': self._event_ids},),
        )
        async for level, batch in readahead_by_level(event_iter, limit=STARKNET_SUBSQUID_READAHEAD_LIMIT):
            yield level, batch
