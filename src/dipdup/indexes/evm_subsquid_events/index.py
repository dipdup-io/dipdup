from typing import Any

from dipdup.config.evm_subsquid_events import SubsquidEventsIndexConfig
from dipdup.datasources.evm_subsquid import SubsquidDatasource
from dipdup.index import Index
from dipdup.models.tezos_tzkt import TzktMessageType


class SubsquidEventsIndex(
    Index[SubsquidEventsIndexConfig, Any, SubsquidDatasource],
    message_type=TzktMessageType.event,
):
    ...
