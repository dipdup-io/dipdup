from collections import deque
from typing import Any

from dipdup.config.tezos_tzkt_events import TzktEventsHandlerConfig
from dipdup.config.tezos_tzkt_events import TzktEventsHandlerConfigU
from dipdup.config.tezos_tzkt_events import TzktEventsIndexConfig
from dipdup.exceptions import ConfigInitializationException
from dipdup.exceptions import FrameworkException
from dipdup.indexes.tezos_tzkt import TzktIndex
from dipdup.indexes.tezos_tzkt_events.fetcher import EventFetcher
from dipdup.indexes.tezos_tzkt_events.matcher import match_events
from dipdup.models.tezos_tzkt import TzktEvent
from dipdup.models.tezos_tzkt import TzktEventData
from dipdup.models.tezos_tzkt import TzktMessageType
from dipdup.models.tezos_tzkt import TzktRollbackMessage
from dipdup.models.tezos_tzkt import TzktUnknownEvent

EventQueueItem = tuple[TzktEventData, ...] | TzktRollbackMessage


class TzktEventsIndex(
    TzktIndex[TzktEventsIndexConfig, EventQueueItem],
    message_type=TzktMessageType.event,
):
    def push_events(self, events: EventQueueItem) -> None:
        self.push_realtime_message(events)

    def _create_fetcher(self, first_level: int, last_level: int) -> EventFetcher:
        event_addresses = self._get_event_addresses()
        event_tags = self._get_event_tags()
        return EventFetcher(
            datasource=self._datasource,
            first_level=first_level,
            last_level=last_level,
            event_addresses=event_addresses,
            event_tags=event_tags,
        )

    async def _synchronize(self, sync_level: int) -> None:
        """Fetch operations via Fetcher and pass to message callback"""
        index_level = await self._enter_sync_state(sync_level)
        if index_level is None:
            return

        first_level = index_level + 1
        self._logger.info('Fetching contract events from level %s to %s', first_level, sync_level)
        fetcher = self._create_fetcher(first_level, sync_level)

        async for _, events in fetcher.fetch_by_level():
            await self._process_level_data(events, sync_level)

        await self._exit_sync_state(sync_level)

    async def _call_matched_handler(
        self, handler_config: TzktEventsHandlerConfigU, level_data: TzktEvent[Any] | TzktUnknownEvent
    ) -> None:
        if isinstance(handler_config, TzktEventsHandlerConfig) != isinstance(level_data, TzktEvent):
            raise FrameworkException(f'Invalid handler config and event types: {handler_config}, {level_data}')

        if not handler_config.parent:
            raise ConfigInitializationException

        await self._ctx.fire_handler(
            handler_config.callback,
            handler_config.parent.name,
            self.datasource,
            str(level_data.data.transaction_id),
            level_data,
        )

    def _get_event_addresses(self) -> set[str]:
        """Get addresses to fetch events during initial synchronization"""
        addresses = set()
        for handler_config in self._config.handlers:
            addresses.add(handler_config.contract.get_address())
        return addresses

    def _get_event_tags(self) -> set[str]:
        """Get tags to fetch events during initial synchronization"""
        paths = set()
        for handler_config in self._config.handlers:
            if isinstance(handler_config, TzktEventsHandlerConfig):
                paths.add(handler_config.tag)
        return paths

    def _match_level_data(self, handlers: Any, level_data: Any) -> deque[Any]:
        return match_events(self._ctx.package, handlers, level_data)
