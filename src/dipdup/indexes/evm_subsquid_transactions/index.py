from collections import deque

from dipdup.config.evm_subsquid_transactions import SubsquidTransactionsIndexConfig
from dipdup.datasources.evm_subsquid import SubsquidDatasource
from dipdup.indexes.evm_subsquid import SubsquidIndex
from dipdup.indexes.evm_subsquid_transactions.fetcher import TransactionFetcher
from dipdup.models.evm_node import EvmNodeTransactionData
from dipdup.models.evm_subsquid import SubsquidMessageType
from dipdup.models.evm_subsquid import TransactionRequest


class SubsquidTransactionsIndex(
    SubsquidIndex[SubsquidTransactionsIndexConfig, EvmNodeTransactionData, SubsquidDatasource],
    message_type=SubsquidMessageType.transactions,
):
    async def _process_queue(self) -> None:
        raise NotImplementedError

    async def _synchronize(self, sync_level: int) -> None:
        raise NotImplementedError

    def _create_fetcher(self, first_level: int, last_level: int) -> TransactionFetcher:

        filters: deque[TransactionRequest] = deque()
        for handler_config in self._config.handlers:
            query: TransactionRequest = {}
            if from_ := handler_config.from_:
                if not from_.address:
                    raise NotImplementedError
                query['from'] = [from_.address]
            if to_ := handler_config.to:
                if not to_.address:
                    raise NotImplementedError
                query['to'] = [to_.address]
            if handler_config.to and handler_config.method:
                method_abi = self._ctx.package.get_converted_abi(handler_config.to.module_name)['methods'][
                    handler_config.method
                ]
                query['sighash'] = [method_abi['sighash']]
            if not query:
                raise NotImplementedError
            filters.append(query)

        return TransactionFetcher(
            datasource=self._datasource,
            first_level=first_level,
            last_level=last_level,
            filters=tuple(filters),
        )
