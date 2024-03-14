import asyncio
import logging
import random
from abc import ABC
from collections import defaultdict
from collections import deque
from datetime import UTC
from datetime import datetime
from typing import Any
from typing import Generic

from dipdup.datasources.evm_node import EvmNodeDatasource
from dipdup.exceptions import FrameworkException
from dipdup.fetcher import DataFetcher
from dipdup.fetcher import FetcherBufferT

_logger = logging.getLogger(__name__)


class EvmNodeFetcher(Generic[FetcherBufferT], DataFetcher[FetcherBufferT], ABC):
    def __init__(
        self,
        datasources: tuple[EvmNodeDatasource, ...],
        first_level: int,
        last_level: int,
    ) -> None:
        super().__init__(datasources[0], first_level, last_level)
        self._datasources = datasources

        self._batch_size_min = 10
        self._batch_size_max = 10000
        self._batch_size_decrease = 0.5
        self._batch_size_increase = 1.1

    def get_next_batch_size(self, batch_size: int, ratelimited: bool) -> int:
        if ratelimited:
            batch_size = int(batch_size * self._batch_size_decrease)
        else:
            batch_size = int(batch_size * self._batch_size_increase)

        batch_size = min(self._batch_size_max, batch_size)
        batch_size = max(self._batch_size_min, batch_size)
        return int(batch_size)

    async def get_block_timestamp(self, level: int) -> datetime:
        block = (await self.get_blocks_batch({level}))[level]
        last_time = block['timestamp']
        return datetime.fromtimestamp(last_time, UTC)

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
