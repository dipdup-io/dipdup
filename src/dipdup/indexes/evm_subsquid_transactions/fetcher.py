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
from dipdup.models.evm_node import EvmNodeTransactionData
from dipdup.models.evm_subsquid import SubsquidTransactionData
from dipdup.models.evm_subsquid import TransactionRequest


class SubsquidTransactionFetcher(DataFetcher[SubsquidTransactionData]):
    """Fetches transactions from REST API, merges them and yields by level."""

    _datasource: SubsquidDatasource

    def __init__(
        self,
        datasource: SubsquidDatasource,
        first_level: int,
        last_level: int,
        filters: tuple[TransactionRequest, ...],
    ) -> None:
        super().__init__(datasource, first_level, last_level)
        self._filters = filters

    async def fetch_by_level(self) -> AsyncIterator[tuple[int, tuple[SubsquidTransactionData, ...]]]:
        transaction_iter = self._datasource.iter_transactions(
            self._first_level,
            self._last_level,
            self._filters,
        )
        async for level, batch in readahead_by_level(transaction_iter, limit=SUBSQUID_READAHEAD_LIMIT):
            yield level, batch


class EvmNodeTransactionFetcher(EvmNodeFetcher[EvmNodeTransactionData]):
    _datasource: EvmNodeDatasource

    async def fetch_by_level(self) -> AsyncIterator[tuple[int, tuple[EvmNodeTransactionData, ...]]]:
        transaction_iter = self._fetch_by_level()
        async for level, batch in readahead_by_level(transaction_iter, limit=EVM_NODE_READAHEAD_LIMIT):
            yield level, batch

    async def _fetch_by_level(self) -> AsyncIterator[tuple[EvmNodeTransactionData, ...]]:
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

            block_batch = await self.get_blocks_batch(
                levels=set(range(batch_first_level, batch_last_level + 1)),
                full_transactions=True,
                node=node,
            )
            blocks = sorted(block_batch.values(), key=lambda block: int(block['number'], 16))

            finished = time.time()
            if finished - started >= node._http_config.ratelimit_sleep:
                ratelimited = True

            for block in blocks:
                timestamp = int(block['timestamp'], 16)
                if not block['transactions']:
                    continue

                parsed_level_transactions = tuple(
                    EvmNodeTransactionData.from_json(transaction, timestamp) for transaction in block['transactions']
                )

                yield parsed_level_transactions

            batch_first_level = batch_last_level + 1
