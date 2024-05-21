from collections import deque
from collections.abc import Iterable
from typing import TYPE_CHECKING
from typing import Any

from dipdup.config.starknet_events import StarknetEventsHandlerConfig
from dipdup.config.starknet_events import StarknetEventsIndexConfig
from dipdup.datasources.starknet_subsquid import StarknetSubsquidDatasource
from dipdup.exceptions import ConfigInitializationException
from dipdup.indexes.starknet import StarknetIndex
from dipdup.indexes.starknet_events.fetcher import StarknetSubsquidEventFetcher
from dipdup.indexes.starknet_events.matcher import match_events
from dipdup.models import RollbackMessage
from dipdup.models.starknet import StarknetEvent
from dipdup.models.starknet import StarknetEventData
from dipdup.models.subsquid import SubsquidMessageType
from dipdup.prometheus import Metrics

QueueItem = tuple[StarknetEventData, ...] | RollbackMessage
# TODO: Potentially starknet node could be another datasource
StarknetDatasource = StarknetSubsquidDatasource

if TYPE_CHECKING:
    from dipdup.context import DipDupContext


class StarknetEventsIndex(
    StarknetIndex[StarknetEventsIndexConfig, QueueItem, StarknetDatasource],
    message_type=SubsquidMessageType.logs,
):
    def __init__(
        self,
        ctx: 'DipDupContext',
        config: StarknetEventsIndexConfig,
        datasources: tuple[StarknetDatasource, ...],
    ) -> None:
        super().__init__(ctx, config, datasources)

    async def _synchronize_subsquid(self, sync_level: int) -> None:
        first_level = self.state.level + 1
        fetcher = self._create_subsquid_fetcher(first_level, sync_level)

        async for _level, events in fetcher.fetch_by_level():
            await self._process_level_data(events, sync_level)
            Metrics.set_sqd_processor_last_block(_level)

    def _create_subsquid_fetcher(self, first_level: int, last_level: int) -> StarknetSubsquidEventFetcher:
        return StarknetSubsquidEventFetcher(
            datasources=self.subsquid_datasources,
            first_level=first_level,
            last_level=last_level,
        )

    def _match_level_data(
        self,
        handlers: tuple[StarknetEventsHandlerConfig, ...],
        level_data: Iterable[StarknetEventData],
    ) -> deque[Any]:
        return match_events(self._ctx.package, handlers, level_data)

    async def _call_matched_handler(
        self,
        handler_config: StarknetEventsHandlerConfig,
        event: StarknetEvent[Any],
    ) -> None:
        if not handler_config.parent:
            raise ConfigInitializationException

        await self._ctx.fire_handler(
            handler_config.callback,
            handler_config.parent.name,
            None,
            event,
        )
