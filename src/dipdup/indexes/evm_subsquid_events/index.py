from contextlib import ExitStack
from typing import Any
from typing import cast

from dipdup.config.evm_subsquid_events import SubsquidEventsHandlerConfig
from dipdup.config.evm_subsquid_events import SubsquidEventsIndexConfig
from dipdup.context import DipDupContext
from dipdup.datasources.evm_node import EvmNodeDatasource
from dipdup.datasources.evm_subsquid import SubsquidDatasource
from dipdup.exceptions import ConfigInitializationException
from dipdup.exceptions import FrameworkException
from dipdup.index import Index
from dipdup.indexes.evm_subsquid_events.fetcher import EventLogFetcher
from dipdup.indexes.evm_subsquid_events.matcher import match_events
from dipdup.models.evm_node import EvmNodeLogData
from dipdup.models.evm_subsquid import SubsquidEvent
from dipdup.models.evm_subsquid import SubsquidEventData
from dipdup.models.evm_subsquid import SubsquidMessageType
from dipdup.prometheus import Metrics


class SubsquidEventsIndex(
    Index[SubsquidEventsIndexConfig, EvmNodeLogData, SubsquidDatasource],
    message_type=SubsquidMessageType.logs,
):
    def __init__(self, ctx: DipDupContext, config: SubsquidEventsIndexConfig, datasource: SubsquidDatasource) -> None:
        super().__init__(ctx, config, datasource)
        self.node_datasource: EvmNodeDatasource | None = None
        if config.datasource.node is not None:
            self.node_datasource = ctx.get_evm_node_datasource(config.datasource.node.name)

    async def _process_queue(self) -> None:
        while self._queue:
            logs = self._queue.popleft()
            message_level = int(logs.block_number, 16)
            if message_level <= self.state.level:
                self._logger.debug('Skipping outdated message: %s <= %s', message_level, self.state.level)
                continue

            # NOTE: If it's not a next block - resync with Subsquid
            if message_level != self.state.level + 1:
                self._logger.info('Not enough realtime messages, resyncing with Subsquid')
                if self.node_datasource is None:
                    raise FrameworkException('Processing queue but node datasource is not set')
                self.datasource.set_sync_level(None, message_level)
                self.node_datasource.set_sync_level(None, message_level)
                return

            with ExitStack() as stack:
                if Metrics.enabled:
                    stack.enter_context(Metrics.measure_level_realtime_duration())
                await self._process_level_events((logs,), message_level)

    def get_sync_level(self) -> int:
        """Get level index needs to be synchronized to depending on its subscription status"""
        sync_levels = set()
        for sub in self._config.get_subscriptions():
            sync_levels.add(self.datasource.get_sync_level(sub))
            if self.node_datasource is not None:
                sync_levels.add(self.node_datasource.get_sync_level(sub))

        if not sync_levels:
            raise FrameworkException('Initialize config before starting `IndexDispatcher`')
        # FIXME: idk
        # if None in sync_levels:
        #     raise FrameworkException('Call `set_sync_level` before starting `IndexDispatcher`')
        if None in sync_levels:
            sync_levels.remove(None)

        # NOTE: Multiple sync levels means index with new subscriptions was added in runtime.
        # NOTE: Choose the highest level; outdated realtime messages will be dropped from the queue anyway.
        self._logger.debug('Current sync levels: %s', sync_levels)
        return max(cast(set[int], sync_levels))

    async def _synchronize(self, sync_level: int) -> None:
        """Fetch event logs via Fetcher and pass to message callback"""
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

    def _create_fetcher(self, first_level: int, last_level: int) -> EventLogFetcher:
        """Get addresses to fetch events during initial synchronization"""
        addresses = set()
        topics = set()

        for handler_config in self._config.handlers:
            addresses.add(handler_config.contract.address)

            event_abi = self._ctx.package.get_evm_events(handler_config.contract.module_name)[handler_config.name]
            topics.add(event_abi.topic0)

        return EventLogFetcher(
            datasource=self._datasource,
            first_level=first_level,
            last_level=last_level,
            addresses=addresses,
            topics=topics,
        )

    async def _process_level_events(
        self,
        events: tuple[SubsquidEventData | EvmNodeLogData, ...],
        sync_level: int,
    ) -> None:
        if not events:
            return

        batch_level = events[0].level
        index_level = self.state.level
        if batch_level <= index_level:
            raise FrameworkException(f'Batch level is lower than index level: {batch_level} <= {index_level}')

        self._logger.debug('Processing contract events of level %s', batch_level)
        matched_handlers = match_events(self._ctx.package, self._config.handlers, events)

        if Metrics.enabled:
            Metrics.set_index_handlers_matched(len(matched_handlers))

        # NOTE: We still need to bump index level but don't care if it will be done in existing transaction
        if not matched_handlers:
            await self._update_state(level=batch_level)
            return

        async with self._ctx._transactions.in_transaction(batch_level, sync_level, self.name):
            for handler_config, event in matched_handlers:
                await self._call_matched_handler(handler_config, event)
            await self._update_state(level=batch_level)

    async def _call_matched_handler(
        self,
        handler_config: SubsquidEventsHandlerConfig,
        event: SubsquidEvent[Any],
    ) -> None:
        if isinstance(handler_config, SubsquidEventsHandlerConfig) != isinstance(event, SubsquidEvent):
            raise FrameworkException(f'Invalid handler config and event types: {handler_config}, {event}')

        if not handler_config.parent:
            raise ConfigInitializationException

        await self._ctx._fire_handler(
            handler_config.callback,
            handler_config.parent.name,
            self.datasource,
            None,
            event,
        )
