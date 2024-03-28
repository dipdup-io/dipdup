import random
import time
from collections.abc import AsyncIterator

from dipdup.datasources.evm_node import EvmNodeDatasource
from dipdup.datasources.evm_subsquid import SubsquidDatasource
from dipdup.fetcher import DataFetcher
from dipdup.fetcher import readahead_by_level
from dipdup.indexes.evm_node import EVM_NODE_READAHEAD_LIMIT
from dipdup.indexes.evm_node import MIN_BATCH_SIZE
from dipdup.indexes.evm_node import EvmNodeFetcher
from dipdup.indexes.evm_subsquid import SUBSQUID_READAHEAD_LIMIT
from dipdup.models.evm_node import EvmNodeLogData
from dipdup.models.evm_subsquid import SubsquidEventData


class SubsquidEventFetcher(DataFetcher[SubsquidEventData]):
    _datasource: SubsquidDatasource

    def __init__(
        self,
        datasource: SubsquidDatasource,
        first_level: int,
        last_level: int,
        topics: tuple[tuple[str | None, str], ...],
    ) -> None:
        super().__init__(datasource, first_level, last_level)
        self._topics = topics

    async def fetch_by_level(self) -> AsyncIterator[tuple[int, tuple[SubsquidEventData, ...]]]:
        event_iter = self._datasource.iter_event_logs(
            self._topics,
            self._first_level,
            self._last_level,
        )
        async for level, batch in readahead_by_level(event_iter, limit=SUBSQUID_READAHEAD_LIMIT):
            yield level, batch


class EvmNodeEventFetcher(EvmNodeFetcher[EvmNodeLogData]):
    _datasource: EvmNodeDatasource

    async def fetch_by_level(self) -> AsyncIterator[tuple[int, tuple[EvmNodeLogData, ...]]]:
        event_iter = self._fetch_by_level()
        async for level, batch in readahead_by_level(event_iter, limit=EVM_NODE_READAHEAD_LIMIT):
            yield level, batch

    async def _fetch_by_level(self) -> AsyncIterator[tuple[EvmNodeLogData, ...]]:
        batch_size = MIN_BATCH_SIZE
        batch_first_level = self._first_level
        ratelimited: bool = False

        while batch_first_level <= self._last_level:
            node = random.choice(self._datasources)
            batch_size = self.get_next_batch_size(batch_size, ratelimited)
            ratelimited = False

            started = time.time()

            batch_last_level = min(
                batch_first_level + batch_size,
                self._last_level,
            )
            log_batch = await self.get_logs_batch(
                batch_first_level,
                batch_last_level,
                node,
            )

            finished = time.time()
            if finished - started >= node._http_config.ratelimit_sleep:
                ratelimited = True

            timestamps: dict[int, int] = {}
            log_levels = list(log_batch.keys())

            # NOTE: Split log_levels to chunks of batch_size
            log_level_batches = [set(log_levels[i : i + batch_size]) for i in range(0, len(log_levels), batch_size)]

            for log_level_batch in log_level_batches:

                started = time.time()

                block_batch = await self.get_blocks_batch(log_level_batch)
                for level, block in block_batch.items():
                    timestamps[level] = int(block['timestamp'], 16)

                finished = time.time()
                if finished - started >= node._http_config.ratelimit_sleep:
                    ratelimited = True

            for level, level_logs in log_batch.items():
                if not level_logs:
                    continue

                parsed_level_logs = tuple(EvmNodeLogData.from_json(log, timestamps[level]) for log in level_logs)

                yield parsed_level_logs

            batch_first_level = batch_last_level + 1
