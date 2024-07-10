from typing import Any
from typing import Generic

from dipdup.fetcher import BufferT
from dipdup.indexes.evm_node import EvmNodeFetcher


class StarknetNodeFetcher(EvmNodeFetcher[Any], Generic[BufferT]): ...
