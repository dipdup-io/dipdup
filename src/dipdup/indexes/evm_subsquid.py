from abc import ABC
from typing import Generic

from dipdup.datasources.evm_subsquid import EvmSubsquidDatasource
from dipdup.fetcher import BufferT
from dipdup.fetcher import DataFetcher


class EvmSubsquidFetcher(Generic[BufferT], DataFetcher[BufferT, EvmSubsquidDatasource], ABC):
    pass
