from dipdup.config.evm_subsquid_transactions import SubsquidTransactionsIndexConfig
from dipdup.datasources.evm_subsquid import SubsquidDatasource
from dipdup.index import Index
from dipdup.models.evm_node import EvmNodeTransactionData
from dipdup.models.evm_subsquid import SubsquidMessageType


class SubsquidTransactionsIndex(
    Index[SubsquidTransactionsIndexConfig, EvmNodeTransactionData, SubsquidDatasource],
    message_type=SubsquidMessageType.transactions,
):
    async def _process_queue(self) -> None:
        return await super()._process_queue()

    async def _synchronize(self, sync_level: int) -> None:
        return await super()._synchronize(sync_level)
