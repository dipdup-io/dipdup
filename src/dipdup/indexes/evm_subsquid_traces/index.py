from dipdup.config.evm_subsquid_traces import EvmSubsquidTracesIndexConfig
from dipdup.datasources.evm_subsquid import SubsquidDatasource
from dipdup.indexes.evm_subsquid import SubsquidIndex
from dipdup.models import RollbackMessage
from dipdup.models.evm_node import EvmNodeTraceData
from dipdup.models.subsquid import SubsquidMessageType

QueueItem = tuple[EvmNodeTraceData, ...] | RollbackMessage


class EvmSubsquidTracesIndex(
    SubsquidIndex[EvmSubsquidTracesIndexConfig, QueueItem, SubsquidDatasource],
    message_type=SubsquidMessageType.traces,
): ...
