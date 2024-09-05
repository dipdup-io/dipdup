from abc import ABC
from typing import Generic

from dipdup.datasources.starknet_node import StarknetNodeDatasource
from dipdup.fetcher import BufferT
from dipdup.fetcher import DataFetcher

STARKNET_NODE_READAHEAD_LIMIT = 100


class StarknetNodeFetcher(Generic[BufferT], DataFetcher[BufferT, StarknetNodeDatasource], ABC):
    def __init__(
        self,
        name: str,
        datasources: tuple[StarknetNodeDatasource, ...],
        first_level: int,
        last_level: int,
    ) -> None:
        super().__init__(
            name=name,
            datasources=datasources,
            first_level=first_level,
            last_level=last_level,
            readahead_limit=STARKNET_NODE_READAHEAD_LIMIT,
        )
