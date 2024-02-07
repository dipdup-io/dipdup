from collections import deque
from typing import Any

from dipdup.config.evm_subsquid_transactions import SubsquidTransactionsHandlerConfig
from dipdup.config.evm_subsquid_transactions import SubsquidTransactionsIndexConfig
from dipdup.datasources.evm_node import NODE_BATCH_SIZE
from dipdup.datasources.evm_subsquid import SubsquidDatasource
from dipdup.exceptions import ConfigInitializationException
from dipdup.indexes.evm_subsquid import SubsquidIndex
from dipdup.indexes.evm_subsquid import get_sighash
from dipdup.indexes.evm_subsquid_transactions.fetcher import TransactionFetcher
from dipdup.indexes.evm_subsquid_transactions.matcher import match_transactions
from dipdup.models.evm_node import EvmNodeTransactionData
from dipdup.models.evm_subsquid import SubsquidMessageType
from dipdup.models.evm_subsquid import SubsquidTransaction
from dipdup.models.evm_subsquid import TransactionRequest
from dipdup.prometheus import Metrics


class SubsquidTransactionsIndex(
    SubsquidIndex[SubsquidTransactionsIndexConfig, tuple[EvmNodeTransactionData, ...], SubsquidDatasource],
    message_type=SubsquidMessageType.transactions,
):
    async def _process_queue(self) -> None:
        while self._queue:
            transactions = self._queue.popleft()
            level = transactions[0].level
            self._logger.info('Processing %s transactions of level %s', len(transactions), level)
            await self._process_level_data(transactions, level)
            Metrics.set_sqd_processor_last_block(level)

    def _match_level_data(self, handlers: Any, level_data: Any) -> deque[Any]:
        return match_transactions(self._ctx.package, handlers, level_data)

    async def _call_matched_handler(
        self,
        handler_config: SubsquidTransactionsHandlerConfig,
        transaction: SubsquidTransaction[Any],
    ) -> None:
        if not handler_config.parent:
            raise ConfigInitializationException

        await self._ctx.fire_handler(
            handler_config.callback,
            handler_config.parent.name,
            self.datasource,
            None,
            transaction,
        )

    async def _synchronize_subsquid(self, sync_level: int) -> None:
        first_level = self.state.level + 1
        fetcher = self._create_fetcher(first_level, sync_level)

        async for _level, transactions in fetcher.fetch_by_level():
            await self._process_level_data(transactions, sync_level)
            Metrics.set_sqd_processor_last_block(_level)

    async def _synchronize_node(self, sync_level: int) -> None:
        batch_first_level = self.state.level + 1
        while batch_first_level <= sync_level:
            batch_last_level = min(batch_first_level + NODE_BATCH_SIZE, sync_level)

            block_batch = await self.get_blocks_batch(
                levels=set(range(batch_first_level, batch_last_level + 1)),
                full_transactions=True,
            )

            for level, block in sorted(block_batch.items()):
                timestamp = int(block['timestamp'], 16)
                parsed_transactions = tuple(
                    EvmNodeTransactionData.from_json(transaction, timestamp) for transaction in block['transactions']
                )

                await self._process_level_data(parsed_transactions, sync_level)
                Metrics.set_sqd_processor_last_block(level)

            batch_first_level = batch_last_level + 1

    def _create_fetcher(self, first_level: int, last_level: int) -> TransactionFetcher:

        filters: deque[TransactionRequest] = deque()
        for handler_config in self._config.handlers:
            query: TransactionRequest = {}
            if (from_ := handler_config.from_) and from_.address:
                query['from'] = [from_.address]
            if (to_ := handler_config.to) and to_.address:
                query['to'] = [to_.address]
            if method := handler_config.method:
                query['sighash'] = [get_sighash(self._ctx.package, method, to_)]
            if not query:
                raise NotImplementedError
            filters.append(query)

        return TransactionFetcher(
            datasource=self._datasource,
            first_level=first_level,
            last_level=last_level,
            filters=tuple(filters),
        )
