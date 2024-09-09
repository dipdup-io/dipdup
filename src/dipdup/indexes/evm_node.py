import asyncio
import logging
import random
from abc import ABC
from collections import defaultdict
from collections import deque
from typing import Any
from typing import Generic

from dipdup.datasources.evm_node import EvmNodeDatasource
from dipdup.exceptions import FrameworkException
from dipdup.fetcher import BufferT
from dipdup.fetcher import DataFetcher

EVM_NODE_READAHEAD_LIMIT = 2500
MIN_BATCH_SIZE = 10
MAX_BATCH_SIZE = 10000
BATCH_SIZE_UP = 1.1
BATCH_SIZE_DOWN = 0.65


_logger = logging.getLogger(__name__)


class EvmNodeFetcher(Generic[BufferT], DataFetcher[BufferT, EvmNodeDatasource], ABC):
    def __init__(
        self,
        name: str,
        datasources: tuple[EvmNodeDatasource, ...],
        first_level: int,
        last_level: int,
    ) -> None:
        super().__init__(
            name=name,
            datasources=datasources,
            first_level=first_level,
            last_level=last_level,
            readahead_limit=EVM_NODE_READAHEAD_LIMIT,
        )

    def get_next_batch_size(self, batch_size: int, ratelimited: bool) -> int:
        old_batch_size = batch_size
        if ratelimited:
            batch_size = int(batch_size * BATCH_SIZE_DOWN)
        else:
            batch_size = int(batch_size * BATCH_SIZE_UP)

        batch_size = min(MAX_BATCH_SIZE, batch_size)
        batch_size = int(max(MIN_BATCH_SIZE, batch_size))
        if batch_size != old_batch_size:
            _logger.debug('Batch size updated: %s -> %s', old_batch_size, batch_size)
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

    async def get_events_batch(
        self,
        first_level: int,
        last_level: int,
        addresses: set[str] | None = None,
        node: EvmNodeDatasource | None = None,
    ) -> dict[int, list[dict[str, Any]]]:
        grouped_events: defaultdict[int, list[dict[str, Any]]] = defaultdict(list)
        node = node or self.get_random_node()
        params: dict[str, Any] = {
            'fromBlock': hex(first_level),
            'toBlock': hex(last_level),
        }
        if addresses:
            params['address'] = list(addresses)
        logs = await node.get_events(params)
        for log in logs:
            grouped_events[int(log['blockNumber'], 16)].append(log)
        return grouped_events
