from abc import ABC
from typing import Generic

from dipdup.datasources.starknet_node import StarknetNodeDatasource
from dipdup.fetcher import BufferT
from dipdup.fetcher import DataFetcher


class StarknetNodeFetcher(Generic[BufferT], DataFetcher[BufferT, StarknetNodeDatasource], ABC): ...
