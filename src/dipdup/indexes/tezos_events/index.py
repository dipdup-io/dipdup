from collections import deque
from typing import Any

from dipdup.config.tezos_events import TezosEventsHandlerConfig
from dipdup.config.tezos_events import TezosEventsIndexConfig
from dipdup.indexes.tezos_events.fetcher import EventFetcher
from dipdup.indexes.tezos_events.matcher import match_events
from dipdup.indexes.tezos_tzkt import TezosIndex
from dipdup.models import RollbackMessage
from dipdup.models.tezos import TezosEventData
from dipdup.models.tezos_tzkt import TezosTzktMessageType

QueueItem = tuple[TezosEventData, ...] | RollbackMessage


class TezosEventsIndex(
    TezosIndex[TezosEventsIndexConfig, QueueItem],
    message_type=TezosTzktMessageType.event,
):
    def _create_fetcher(self, first_level: int, last_level: int) -> EventFetcher:
        event_addresses = self._get_event_addresses()
        event_tags = self._get_event_tags()
        return EventFetcher(
            name=self.name,
            datasources=self._datasources,
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
            if isinstance(handler_config, TezosEventsHandlerConfig):
                paths.add(handler_config.tag)
        return paths

    def _match_level_data(self, handlers: Any, level_data: Any) -> deque[Any]:
        return match_events(self._ctx.package, handlers, level_data)
