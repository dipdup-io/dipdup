import asyncio
from collections import defaultdict
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

LEVEL_TIMEOUT = 1
LAST_MILE_LEVELS = 32


class SubsquidEventsIndex(
    Index[SubsquidEventsIndexConfig, EvmNodeLogData, SubsquidDatasource],
    message_type=SubsquidMessageType.logs,
):
    def __init__(
        self,
        ctx: DipDupContext,
        config: SubsquidEventsIndexConfig,
        datasource: SubsquidDatasource,
    ) -> None:
        super().__init__(ctx, config, datasource)
        self.node_datasource: EvmNodeDatasource | None = None
        if config.datasource.node is not None:
            self.node_datasource = ctx.get_evm_node_datasource(config.datasource.node.name)

    async def _process_queue(self) -> None:
        logs_by_level = defaultdict(list)

        while True:
            while self._queue:
                logs = self._queue.popleft()
                message_level = int(logs.block_number, 16)
                if message_level <= self.state.level:
                    self._logger.debug('Skipping outdated message: %s <= %s', message_level, self.state.level)
                    continue

                logs_by_level[message_level].append(logs)

            # NOTE: Wait for more messages until grouping them by level
            await asyncio.sleep(LEVEL_TIMEOUT)
            if not self._queue:
                break

        for message_level, level_logs in logs_by_level.items():
            # NOTE: If it's not a next block - resync with Subsquid
            if message_level != self.state.level + 1:
                self._logger.warning('Not enough realtime messages, resyncing to %s', message_level)
                self._queue.clear()
                self.datasource.set_sync_level(None, message_level)
                return

            with ExitStack() as stack:
                if Metrics.enabled:
                    stack.enter_context(Metrics.measure_level_realtime_duration())
                await self._process_level_events(tuple(level_logs), message_level)

    def get_sync_level(self) -> int:
        """Get level index needs to be synchronized to depending on its subscription status"""
        sync_levels = set()
        for sub in self._config.get_subscriptions():
            sync_levels.add(self.datasource.get_sync_level(sub))
            if self.node_datasource is not None:
                sync_levels.add(self.node_datasource.get_sync_level(sub))

        if None in sync_levels:
            sync_levels.remove(None)
        if not sync_levels:
            raise FrameworkException('Initialize config before starting `IndexDispatcher`')

        # NOTE: Multiple sync levels means index with new subscriptions was added in runtime.
        # NOTE: Choose the highest level; outdated realtime messages will be dropped from the queue anyway.
        return max(cast(set[int], sync_levels))

    async def _synchronize(self, sync_level: int) -> None:
        """Fetch event logs via Fetcher and pass to message callback"""
        index_level = await self._enter_sync_state(sync_level)
        if index_level is None:
            return

        levels_left = sync_level - index_level
        first_level = index_level + 1

        if levels_left <= 0:
            return
        elif levels_left >= LAST_MILE_LEVELS or not self.node_datasource:
            sync_level = await self.datasource.get_head_level()
            fetcher = self._create_fetcher(first_level, sync_level)

            async for level, events in fetcher.fetch_by_level():
                with ExitStack() as stack:
                    if Metrics.enabled:
                        Metrics.set_levels_to_sync(self._config.name, sync_level - level)
                        stack.enter_context(Metrics.measure_level_sync_duration())
                    await self._process_level_events(events, sync_level)

        else:
            self._logger.info('Not enough realtime messages; syncing with node RPC')
            if self.node_datasource is None:
                raise FrameworkException('Processing queue but node datasource is not set')

            # NOTE: Fetch last blocks from node if there are not enough realtime messages in queue
            self._logger.info('Resyncing with node: %s -> %s', index_level, sync_level)
            for level in range(first_level, sync_level):
                block = await self.node_datasource.get_block_by_level(level)
                if block is None:
                    raise FrameworkException(f'Block {level} not found')
                level_logs = await self.node_datasource.get_logs(
                    {
                        # TODO: Filter by addresses too
                        'fromBlock': hex(level),
                        'toBlock': hex(level),
                    }
                )
                parsed_level_logs = tuple(EvmNodeLogData.from_json(log) for log in level_logs)
                await self._process_level_events(parsed_level_logs, sync_level)

        await self._exit_sync_state(sync_level)

    def _create_fetcher(self, first_level: int, last_level: int) -> EventLogFetcher:
        addresses = set()
        topics = []

        for handler_config in self._config.handlers:
            address = handler_config.contract.address
            if address is not None:
                addresses.add(address)
            elif handler_config.contract.abi is None:
                raise NotImplementedError('Either contract address or ABI must be specified')

            event_abi = self._ctx.package.get_evm_events(handler_config.contract.module_name)[handler_config.name]
            topics.append((address, event_abi.topic0))

        return EventLogFetcher(
            datasource=self._datasource,
            first_level=first_level,
            last_level=last_level,
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
