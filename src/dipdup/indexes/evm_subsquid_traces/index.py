from dipdup.config.evm_subsquid_traces import SubsquidTracesIndexConfig
from dipdup.datasources.evm_subsquid import SubsquidDatasource
from dipdup.index import Index
from dipdup.models.evm_node import EvmNodeTraceData
from dipdup.models.evm_subsquid import SubsquidMessageType


class SubsquidTracesIndex(
    Index[SubsquidTracesIndexConfig, EvmNodeTraceData, SubsquidDatasource],
    message_type=SubsquidMessageType.traces,
):
    ...
