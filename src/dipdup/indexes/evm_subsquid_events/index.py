from typing import Any

from dipdup.config.evm_subsquid_events import EvmSubsquidEventsIndexConfig
from dipdup.datasources.evm_subsquid import EvmSubsquidDatasource
from dipdup.index import Index
from dipdup.models.tezos_tzkt import MessageType


class EvmSubsquidEventsIndex(
    Index[EvmSubsquidEventsIndexConfig, Any, EvmSubsquidDatasource],
    message_type=MessageType.event,
):
    ...
