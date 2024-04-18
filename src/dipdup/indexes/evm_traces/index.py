from dipdup.config.evm_traces import EvmTracesIndexConfig
from dipdup.datasources.evm_subsquid import EvmSubsquidDatasource
from dipdup.indexes.evm_subsquid import SubsquidIndex
from dipdup.models import RollbackMessage
from dipdup.models.evm_node import EvmNodeTraceData
from dipdup.models.subsquid import SubsquidMessageType

QueueItem = tuple[EvmNodeTraceData, ...] | RollbackMessage


class EvmTracesIndex(
    SubsquidIndex[EvmTracesIndexConfig, QueueItem, EvmSubsquidDatasource],
    message_type=SubsquidMessageType.traces,
): ...
