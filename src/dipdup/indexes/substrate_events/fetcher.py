from collections.abc import AsyncIterator

from dipdup.datasources.substrate_subsquid import SubstrateSubsquidDatasource
from dipdup.indexes.substrate_subsquid import SubstrateSubsquidFetcher
from dipdup.models.substrate import SubstrateEventData


class SubstrateSubsquidEventFetcher(SubstrateSubsquidFetcher[SubstrateEventData]):
    def __init__(
        self,
        name: str,
        datasources: tuple[SubstrateSubsquidDatasource, ...],
        first_level: int,
        last_level: int,
        names: tuple[str, ...],
    ) -> None:
        super().__init__(
            name=name,
            datasources=datasources,
            first_level=first_level,
            last_level=last_level,
        )
        self._names = names

    async def fetch_by_level(self) -> AsyncIterator[tuple[int, tuple[SubstrateEventData, ...]]]:
        event_iter = self.random_datasource.iter_events(
            first_level=self._first_level,
            last_level=self._last_level,
            names=self._names,
        )
        async for level, batch in self.readahead_by_level(event_iter):
            yield level, batch
