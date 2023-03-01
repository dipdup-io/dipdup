from typing import Any

from dipdup.config.evm_subsquid_events import SubsquidEventsIndexConfig
from dipdup.datasources.evm_subsquid import SubsquidDatasource
from dipdup.index import Index
from dipdup.models.evm_subsquid import SubsquidMessageType


class SubsquidEventsIndex(
    Index[SubsquidEventsIndexConfig, Any, SubsquidDatasource],
    message_type=SubsquidMessageType.logs,
):
    async def _process_queue(self) -> None:
        ...

    async def _synchronize(self, sync_level: int) -> None:
        ...
