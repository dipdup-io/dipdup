from abc import ABC
from typing import Generic

from dipdup.datasources.starknet_subsquid import StarknetSubsquidDatasource
from dipdup.fetcher import BufferT
from dipdup.fetcher import DataFetcher

STARKNET_SUBSQUID_READAHEAD_LIMIT = 10000


class StarknetSubsquidFetcher(Generic[BufferT], DataFetcher[BufferT, StarknetSubsquidDatasource], ABC):
    def __init__(
        self,
        name: str,
        datasources: tuple[StarknetSubsquidDatasource, ...],
        first_level: int,
        last_level: int,
    ) -> None:
        super().__init__(
            name=name,
            datasources=datasources,
            first_level=first_level,
            last_level=last_level,
            readahead_limit=STARKNET_SUBSQUID_READAHEAD_LIMIT,
        )
