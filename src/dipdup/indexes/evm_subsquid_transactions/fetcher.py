from collections.abc import AsyncIterator

from dipdup.datasources.evm_subsquid import SubsquidDatasource
from dipdup.fetcher import DataFetcher
from dipdup.fetcher import readahead_by_level
from dipdup.models.evm_subsquid import SubsquidTransactionData
from dipdup.models.evm_subsquid import TransactionRequest


class TransactionFetcher(DataFetcher[SubsquidTransactionData]):
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
