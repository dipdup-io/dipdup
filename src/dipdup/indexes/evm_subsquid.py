from abc import ABC
from typing import Generic

from dipdup.datasources.evm_subsquid import EvmSubsquidDatasource
from dipdup.fetcher import BufferT
from dipdup.fetcher import DataFetcher

EVM_SUBSQUID_READAHEAD_LIMIT = 10000


class EvmSubsquidFetcher(Generic[BufferT], DataFetcher[BufferT, EvmSubsquidDatasource], ABC):
    def __init__(
        self,
        name: str,
        datasources: tuple[EvmSubsquidDatasource, ...],
        first_level: int,
        last_level: int,
    ) -> None:
        super().__init__(
            name=name,
            datasources=datasources,
            first_level=first_level,
            last_level=last_level,
            readahead_limit=EVM_SUBSQUID_READAHEAD_LIMIT,
        )
