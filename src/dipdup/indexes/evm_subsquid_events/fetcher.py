# from typing import AsyncIterator
from dipdup.datasources.evm_subsquid import SubsquidDatasource
from dipdup.fetcher import DataFetcher
from dipdup.models.evm_subsquid import SubsquidEventData


class EventFetcher(DataFetcher[SubsquidEventData]):
    def __init__(
        self,
        datasource: SubsquidDatasource,
        first_level: int,
        last_level: int,
        addresses: set[str],
        topics: set[str],
    ) -> None:
        super().__init__(datasource, first_level, last_level)
        self._addresses = addresses
        self._topics = topics

    # async def fetch_by_level(self) -> AsyncIterator[tuple[int, tuple[SubsquidEventData, ...]]]:
    #     ...
