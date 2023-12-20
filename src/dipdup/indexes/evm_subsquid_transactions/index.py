from dipdup.config.evm_subsquid_transactions import SubsquidTransactionsIndexConfig
from dipdup.datasources.evm_subsquid import SubsquidDatasource
from dipdup.indexes.evm_subsquid import SubsquidIndex
from dipdup.models.evm_node import EvmNodeTransactionData
from dipdup.models.evm_subsquid import SubsquidMessageType


class SubsquidTransactionsIndex(
    SubsquidIndex[SubsquidTransactionsIndexConfig, EvmNodeTransactionData, SubsquidDatasource],
    message_type=SubsquidMessageType.transactions,
):
    async def _process_queue(self) -> None:
        raise NotImplementedError

    async def _synchronize(self, sync_level: int) -> None:
        raise NotImplementedError
