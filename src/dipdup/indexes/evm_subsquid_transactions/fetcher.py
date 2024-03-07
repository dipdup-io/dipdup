from collections.abc import AsyncIterator

from dipdup.datasources.evm_node import EvmNodeDatasource
from dipdup.datasources.evm_subsquid import SubsquidDatasource
from dipdup.fetcher import DataFetcher
from dipdup.fetcher import readahead_by_level
from dipdup.indexes.evm_node import EvmNodeFetcher
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
        """Iterate over transactions fetched fetched from REST.

        Resulting data is splitted by level, deduped, sorted and ready to be processed by SubsquidTransactionsIndex.
        """
        transaction_iter = self._datasource.iter_transactions(
            self._first_level,
            self._last_level,
            self._filters,
        )
        async for level, batch in readahead_by_level(transaction_iter, limit=5_000):
            yield level, batch


class EvmNodeTransactionFetcher(EvmNodeFetcher[EvmNodeTransactionData]):
    _datasource: EvmNodeDatasource

    async def _fetch_by_level(self) -> AsyncIterator[tuple[EvmNodeTransactionData, ...]]:
        batch_first_level = self._first_level
        while batch_first_level <= self._last_level:
            node = self.get_random_node()
            batch_last_level = min(
                batch_first_level + node._http_config.batch_size,
                self._last_level,
            )

            block_batch = await self.get_blocks_batch(
                levels=set(range(batch_first_level, batch_last_level + 1)),
                full_transactions=True,
                node=node,
            )

            for _, block in sorted(block_batch.items()):
                timestamp = int(block['timestamp'], 16)
                parsed_transactions = tuple(
                    EvmNodeTransactionData.from_json(transaction, timestamp) for transaction in block['transactions']
                )

                yield parsed_transactions

            batch_first_level = batch_last_level + 1

    async def fetch_by_level(self) -> AsyncIterator[tuple[int, tuple[EvmNodeTransactionData, ...]]]:
        transaction_iter = self._fetch_by_level()
        async for level, batch in readahead_by_level(transaction_iter, limit=5_000):
            yield level, batch
