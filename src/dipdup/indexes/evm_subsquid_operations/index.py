from typing import Any

from dipdup.config.evm_subsquid_operations import EvmSubsquidOperationsIndexConfig
from dipdup.datasources.evm_subsquid import SubsquidDatasource
from dipdup.index import Index
from dipdup.models.tezos_tzkt import TzktMessageType


class EvmSubsquidOperationsIndex(
    Index[EvmSubsquidOperationsIndexConfig, Any, SubsquidDatasource],
    message_type=TzktMessageType.operation,
):
    ...
