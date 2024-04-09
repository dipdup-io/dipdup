import asyncio
import random
from abc import ABC
from collections import defaultdict
from collections import deque
from typing import Any
from typing import Generic

from dipdup.datasources.evm_node import EvmNodeDatasource
from dipdup.exceptions import FrameworkException
from dipdup.fetcher import DataFetcher
from dipdup.fetcher import FetcherBufferT

EVM_NODE_READAHEAD_LIMIT = 5000
MIN_BATCH_SIZE = 10
MAX_BATCH_SIZE = 10000
BATCH_SIZE_UP = 1.1
BATCH_SIZE_DOWN = 0.5


class EvmNodeFetcher(Generic[FetcherBufferT], DataFetcher[FetcherBufferT], ABC):
    def __init__(
        self,
        datasources: tuple[EvmNodeDatasource, ...],
        first_level: int,
        last_level: int,
    ) -> None:
        super().__init__(datasources[0], first_level, last_level)
        self._datasources = datasources

    def get_next_batch_size(self, batch_size: int, ratelimited: bool) -> int:
        if ratelimited:
            batch_size = int(batch_size * BATCH_SIZE_DOWN)
        else:
            batch_size = int(batch_size * BATCH_SIZE_UP)

        batch_size = min(MAX_BATCH_SIZE, batch_size)
        batch_size = max(MIN_BATCH_SIZE, batch_size)
        return int(batch_size)

    def get_random_node(self) -> EvmNodeDatasource:
        if not self._datasources:
            raise FrameworkException('A node datasource requested, but none attached to this index')
        return random.choice(self._datasources)

    async def get_blocks_batch(
        self,
        levels: set[int],
        full_transactions: bool = False,
        node: EvmNodeDatasource | None = None,
    ) -> dict[int, dict[str, Any]]:
        tasks: deque[asyncio.Task[Any]] = deque()
        blocks: dict[int, Any] = {}
        node = node or self.get_random_node()

        async def _fetch(level: int) -> None:
            blocks[level] = await node.get_block_by_level(
                block_number=level,
                full_transactions=full_transactions,
            )

        for level in levels:
            tasks.append(
                asyncio.create_task(
                    _fetch(level),
                    name=f'get_block_range:{level}',
                ),
            )

        await asyncio.gather(*tasks)
        return blocks

    async def get_logs_batch(
        self,
        first_level: int,
        last_level: int,
        node: EvmNodeDatasource | None = None,
    ) -> dict[int, list[dict[str, Any]]]:
        grouped_logs: defaultdict[int, list[dict[str, Any]]] = defaultdict(list)
        node = node or self.get_random_node()
        logs = await node.get_logs(
            {
                'fromBlock': hex(first_level),
                'toBlock': hex(last_level),
            },
        )
        for log in logs:
            grouped_logs[int(log['blockNumber'], 16)].append(log)
        return grouped_logs
