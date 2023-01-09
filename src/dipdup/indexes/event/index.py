from contextlib import ExitStack
from typing import Any

from dipdup.config import EventHandlerConfig
from dipdup.config import EventHandlerConfigU
from dipdup.config import EventIndexConfig
from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.enums import MessageType
from dipdup.exceptions import ConfigInitializationException
from dipdup.exceptions import FrameworkException
from dipdup.index import Index
from dipdup.index import extract_level
from dipdup.indexes.event.fetcher import EventFetcher
from dipdup.indexes.event.matcher import match_events
from dipdup.models import Event
from dipdup.models import EventData
from dipdup.models import UnknownEvent
from dipdup.prometheus import Metrics

EventQueueItem = tuple[EventData, ...]


class EventIndex(
    Index[EventIndexConfig, EventQueueItem, TzktDatasource],
    message_type=MessageType.event,
):
    def push_events(self, events: EventQueueItem) -> None:
        self.push_realtime_message(events)

    async def _process_queue(self) -> None:
        """Process WebSocket queue"""
        if self._queue:
            self._logger.debug('Processing websocket queue')
        while self._queue:
            events = self._queue.popleft()
            message_level = events[0].level
            if message_level <= self.state.level:
                self._logger.debug('Skipping outdated message: %s <= %s', message_level, self.state.level)
                continue

            with ExitStack() as stack:
                if Metrics.enabled:
                    stack.enter_context(Metrics.measure_level_realtime_duration())
                await self._process_level_events(events, message_level)

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

        async for level, events in fetcher.fetch_by_level():
            with ExitStack() as stack:
                if Metrics.enabled:
                    Metrics.set_levels_to_sync(self._config.name, sync_level - level)
                    stack.enter_context(Metrics.measure_level_sync_duration())
                await self._process_level_events(events, sync_level)

        await self._exit_sync_state(sync_level)

    async def _process_level_events(
        self,
        events: tuple[EventData, ...],
        sync_level: int,
    ) -> None:
        if not events:
            return

        batch_level = extract_level(events)
        index_level = self.state.level
        if batch_level <= index_level:
            raise FrameworkException(f'Batch level is lower than index level: {batch_level} <= {index_level}')

        self._logger.debug('Processing contract events of level %s', batch_level)
        matched_handlers = match_events(self._config.handlers, events)

        if Metrics.enabled:
            Metrics.set_index_handlers_matched(len(matched_handlers))

        # NOTE: We still need to bump index level but don't care if it will be done in existing transaction
        if not matched_handlers:
            await self.state.update_status(level=batch_level)
            return

        async with self._ctx._transactions.in_transaction(batch_level, sync_level, self.name):
            for handler_config, event in matched_handlers:
                await self._call_matched_handler(handler_config, event)
            await self.state.update_status(level=batch_level)

    async def _call_matched_handler(
        self, handler_config: EventHandlerConfigU, event: Event[Any] | UnknownEvent
    ) -> None:
        if isinstance(handler_config, EventHandlerConfig) != isinstance(event, Event):
            raise FrameworkException(f'Invalid handler config and event types: {handler_config}, {event}')

        if not handler_config.parent:
            raise ConfigInitializationException

        await self._ctx._fire_handler(
            handler_config.callback,
            handler_config.parent.name,
            self.datasource,
            str(event.data.transaction_id),
            event,
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
            if isinstance(handler_config, EventHandlerConfig):
                paths.add(handler_config.tag)
        return paths
