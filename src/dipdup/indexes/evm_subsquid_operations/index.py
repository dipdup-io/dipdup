from typing import Any

from dipdup.config.evm_subsquid_operations import SubsquidOperationsIndexConfig
from dipdup.datasources.evm_subsquid import SubsquidDatasource
from dipdup.index import Index
from dipdup.models.tezos_tzkt import TzktMessageType


class SubsquidOperationsIndex(
    Index[SubsquidOperationsIndexConfig, Any, SubsquidDatasource],
    message_type=TzktMessageType.operation,
):
    ...
