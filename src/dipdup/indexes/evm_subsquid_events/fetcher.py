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

        batch_first_level = self._first_level
        while batch_first_level <= self._last_level:
            node = random.choice(self._datasources)
            batch_last_level = min(
                batch_first_level + node._http_config.batch_size,
                self._last_level,
            )

            log_batch = await self.get_logs_batch(
                first_level=batch_first_level,
                last_level=batch_last_level,
                node=node,
            )
            block_batch = await self.get_blocks_batch(
                levels=set(log_batch.keys()),
                full_transactions=False,
                node=node,
            )

            for level_logs, level_block in zip(log_batch.values(), block_batch.values(), strict=True):
                timestamp = int(level_block['timestamp'], 16)
                parsed_level_logs = tuple(EvmNodeLogData.from_json(log, timestamp) for log in level_logs)

                yield parsed_level_logs

            batch_first_level = batch_last_level + 1

    async def fetch_by_level(self) -> AsyncIterator[tuple[int, tuple[EvmNodeLogData, ...]]]:
        event_iter = self._fetch_by_level()
        async for level, batch in readahead_by_level(event_iter, limit=SUBSQUID_READAHEAD_LIMIT):
            yield level, batch
