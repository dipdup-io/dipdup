from collections import defaultdict
from typing import Any
from typing import Generic

from starknet_py.net.client_models import EmittedEvent

from dipdup.datasources.starknet_node import StarknetNodeDatasource
from dipdup.fetcher import BufferT
from dipdup.indexes.evm_node import EvmNodeFetcher


class StarknetNodeFetcher(EvmNodeFetcher, Generic[BufferT]):
    ...