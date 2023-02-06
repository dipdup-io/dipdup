from typing import Any

from dipdup.config.evm_subsquid_events import EvmSubsquidEventsIndexConfig
from dipdup.datasources.subsquid import SubsquidDatasource
from dipdup.index import Index
from dipdup.models.tzkt import MessageType


class EvmSubsquidEventsIndex(
    Index[EvmSubsquidEventsIndexConfig, Any, SubsquidDatasource],
    message_type=MessageType.event,
):
    ...
