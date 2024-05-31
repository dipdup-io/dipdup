from abc import ABC
from typing import Generic

from dipdup.datasources.starknet_subsquid import StarknetSubsquidDatasource
from dipdup.fetcher import BufferT
from dipdup.fetcher import DataFetcher


class StarknetSubsquidFetcher(Generic[BufferT], DataFetcher[BufferT, StarknetSubsquidDatasource], ABC):
    pass
