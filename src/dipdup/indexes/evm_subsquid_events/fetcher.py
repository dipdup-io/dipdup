from datetime import UTC, datetime
import random
from collections.abc import AsyncIterator

from dipdup.datasources.evm_node import EvmNodeDatasource
from dipdup.datasources.evm_subsquid import SubsquidDatasource
from dipdup.fetcher import DataFetcher
from dipdup.fetcher import readahead_by_level
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

    async def _fetch_by_level(self) -> AsyncIterator[tuple[EvmNodeLogData, ...]]:
        batch_size = self.min_batch_size
        events_found = 0
        batch_first_level = self._first_level
        while batch_first_level <= self._last_level:
            node = random.choice(self._datasources)

            batch_size = self.estimate_next_batch_size(batch_size, events_found)
            print('batch_size:', batch_size)
            batch_last_level = min(
                batch_first_level + batch_size,
                self._last_level,
            )
            log_batch = await self.get_logs_batch(
                batch_first_level,
                batch_last_level,
                node,
            )

            timestamps: dict[int, int] = {}

            log_levels = list(log_batch.keys())
            print('log_levels:', log_levels)

            # NOTE: Split log_levels to chunks of batch_size
            log_level_batches = [
                log_levels[i:i + node._http_config.batch_size]
                for i in range(0, len(log_levels), node._http_config.batch_size)
            ]

            for log_level_batch in log_level_batches:

                block_batch = await self.get_blocks_batch(log_level_batch)
                for level, block in block_batch.items():
                    timestamps[level] = int(block['timestamp'], 16)

            print('timestamps:', len(timestamps))

            for level, level_logs in log_batch.items():
                if not level_logs:
                    continue

                parsed_level_logs = tuple(EvmNodeLogData.from_json(log, timestamps[level]) for log in level_logs)

                yield parsed_level_logs

            batch_first_level = batch_last_level + 1

    async def fetch_by_level(self) -> AsyncIterator[tuple[int, tuple[EvmNodeLogData, ...]]]:
        event_iter = self._fetch_by_level()
        async for level, batch in readahead_by_level(event_iter, limit=SUBSQUID_READAHEAD_LIMIT):
            yield level, batch
