import asyncio
import logging
import random
import time
from abc import ABC
from collections import defaultdict
from collections import deque
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

        max_batch_scan_size: int = 10000
        max_request_retries: int = 30
        request_retry_seconds: float = 3.0

        # Our JSON-RPC throttling parameters
        self.min_batch_size = 10  # 12 s/block = 120 seconds period
        self.max_batch_size = max_batch_scan_size
        self.max_request_retries = max_request_retries
        self.request_retry_seconds = request_retry_seconds

        # Factor how fast we increase the chunk size if results are found
        # # (slow down scan after starting to get hits)
        self.batch_size_decrease = 0.5

        # Factor how fast we increase chunk size if no results found
        self.batch_size_increase = 2.0

    def estimate_next_batch_size(self, current_batch_size: int, event_found_count: int) -> int:
        if event_found_count > 0:
            # When we encounter first events, reset the chunk size window
            current_batch_size = self.min_batch_size
        else:
            current_batch_size = int(current_batch_size * self.batch_size_increase)

        current_batch_size = max(self.min_batch_size, current_batch_size)
        current_batch_size = min(self.max_batch_size, current_batch_size)
        return int(current_batch_size)

    def scan(
        self,
        first_level: int,
        last_level: int,
        initial_batch_size: int = 20,
    ) -> tuple[list[Any], int]:
        assert first_level <= last_level

        current_level = first_level

        # Scan in chunks, commit between
        batch_size = initial_batch_size
        last_scan_duration: float = 0
        last_logs_found: int = 0
        total_levels_scanned = 0

        # All processed entries we got on this scan cycle
        all_processed = []

        while current_level <= last_level:
            # Print some diagnostics to logs to try to fiddle with real world JSON-RPC API performance
            estimated_last_level = current_level + batch_size
            _logger.debug(
                'Scanning token transfers for blocks: {} - {}, chunk size {}, last chunk scan took {}, last logs found {}',
                current_level,
                estimated_last_level,
                batch_size,
                last_scan_duration,
                last_logs_found,
            )

            start = time.time()
            actual_last_level, last_level_timestamp, new_entries = self.scan_batch(current_level, estimated_last_level)

            # Where does our current chunk scan ends - are we out of chain yet?
            current_end = actual_last_level

            last_scan_duration = time.time() - start
            all_processed += new_entries

            # Try to guess how many blocks to fetch over `eth_getLogs` API next time
            batch_size = self.estimate_next_batch_size(batch_size, len(new_entries))

            # Set where the next chunk starts
            current_level = current_end + 1
            total_levels_scanned += 1
            # self.state.end_batch(current_end)

        return all_processed, total_levels_scanned

    def scan_batch(self, first_level: int, last_level: int) -> tuple[int, datetime, list[Any]]:
        block_timestamps = {}
        get_block_timestamp = self.get_block_timestamp

        # Cache block timestamps to reduce some RPC overhead
        # Real solution might include smarter models around block
        def get_block_when(block_num: int) -> Any:
            if block_num not in block_timestamps:
                block_timestamps[block_num] = get_block_timestamp(block_num)
            return block_timestamps[block_num]

        all_processed: list[Any] = []

        for _event_type in self.events:

            events: list[Any] = []

            for evt in events:
                idx = evt['logIndex']  # Integer of the log index position in the block, null when its pending

                # We cannot avoid minor chain reorganisations, but
                # at least we must avoid blocks that are not mined yet
                assert idx is not None, 'Somehow tried to scan a pending block'

                block_number = evt['blockNumber']

                # Get UTC time when this event happened (block mined timestamp)
                # from our in-memory cache
                get_block_when(block_number)

                # _logger.debug(
                #     f"Processing event {evt['event']}, block: {evt['blockNumber']} count: {evt['blockNumber']}"
                # )
                # processed = self.state.process_event(block_when, evt)
                # all_processed.append(processed)

        last_level_timestamp = get_block_when(last_level)
        return last_level, last_level_timestamp, all_processed

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
