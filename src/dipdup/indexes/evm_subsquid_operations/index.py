from typing import Any

from dipdup.config.evm_subsquid_operations import EvmSubsquidOperationsIndexConfig
from dipdup.datasources.evm_subsquid import EvmSubsquidDatasource
from dipdup.index import Index
from dipdup.models.tezos_tzkt import MessageType


class EvmSubsquidOperationsIndex(
    Index[EvmSubsquidOperationsIndexConfig, Any, EvmSubsquidDatasource],
    message_type=MessageType.operation,
):
    ...
