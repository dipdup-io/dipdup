from typing import Any

from dipdup.config.evm_subsquid_operations import EvmSubsquidOperationsIndexConfig
from dipdup.datasources.subsquid import SubsquidDatasource
from dipdup.index import Index
from dipdup.models.tzkt import MessageType


class EvmSubsquidOperationsIndex(
    Index[EvmSubsquidOperationsIndexConfig, Any, SubsquidDatasource],
    message_type=MessageType.operation,
):
    ...
