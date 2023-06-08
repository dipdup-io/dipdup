import asyncio
import random
import time
from collections import defaultdict
from typing import Any
from typing import cast

from dipdup.config.evm_node import EvmNodeDatasourceConfig
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
from dipdup.performance import metrics

LEVEL_BATCH_TIMEOUT = 1
LAST_MILE_TRIGGER = 256
LEVELS_LEFT_TRIGGER = 256


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
        self._node_datasources: tuple[EvmNodeDatasource, ...] | None = None
        self._topics: dict[str, dict[str, str]] | None = None

    @property
    def node_datasources(self) -> tuple[EvmNodeDatasource, ...]:
        if self._node_datasources is not None:
            return self._node_datasources

        node_field = self._config.datasource.node
        if node_field is None:
            node_field = ()
        elif isinstance(node_field, EvmNodeDatasourceConfig):
            node_field = (node_field,)
        self._node_datasources = tuple(
            self._ctx.get_evm_node_datasource(node_config.name) for node_config in node_field
        )
        return self._node_datasources

    @property
    def node_datasource(self) -> EvmNodeDatasource:
        if not self.node_datasources:
            raise FrameworkException('A node datasource requested, but none attached to this index')
        return random.choice(self.node_datasources)

    @property
    def topics(self) -> dict[str, dict[str, str]]:
        if self._topics is None:
            self._topics = {}
            for handler_config in self._config.handlers:
                typename = handler_config.contract.module_name
                self._topics[typename] = self._ctx.package.get_evm_topics(typename)

        return self._topics

    async def _process_queue(self) -> None:
        logs_by_level = defaultdict(list)

        # NOTE: Drain queue and group messages by level.
        while True:
            while self._queue:
                logs = self._queue.popleft()
                message_level = int(logs.block_number, 16)
                if message_level <= self.state.level:
                    self._logger.debug('Skipping outdated message: %s <= %s', message_level, self.state.level)
                    continue

                logs_by_level[message_level].append(logs)

            # NOTE: Wait for more messages a bit more - node doesn't notify us about the level boundaries.
            await asyncio.sleep(LEVEL_BATCH_TIMEOUT)
            if not self._queue:
                break

        for message_level, level_logs in logs_by_level.items():
            # NOTE: If it's not a next block - resync with Subsquid
            if message_level != self.state.level + 1:
                self._logger.info('Not enough messages in queue; resyncing to %s', message_level)
                self._queue.clear()
                self.datasource.set_sync_level(None, message_level)
                return

            await self._process_level_events(tuple(level_logs), self.topics, message_level)

    def get_sync_level(self) -> int:
        """Get level index needs to be synchronized to depending on its subscription status"""
        sync_levels = set()
        for sub in self._config.get_subscriptions():
            sync_levels.add(self.datasource.get_sync_level(sub))
            for datasource in self.node_datasources or ():
                sync_levels.add(datasource.get_sync_level(sub))

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

        subsquid_sync_level = await self.datasource.get_head_level()

        if self.node_datasources:
            node_sync_level = await self.node_datasource.get_head_level()
            last_mile = abs(node_sync_level - subsquid_sync_level)
            self._logger.info('Subsquid is %s levels behind the node; %s levels left to sync', last_mile, levels_left)
        else:
            self._logger.info('Subsquid head is %s; %s levels to sync', subsquid_sync_level, levels_left)
            last_mile, node_datasource = 0, None

        use_node = last_mile < LAST_MILE_TRIGGER and levels_left < LEVELS_LEFT_TRIGGER

        # NOTE: Fetch last blocks from node if there are not enough realtime messages in queue
        if use_node and self.node_datasources:
            sync_level = node_sync_level
            for level in range(first_level, sync_level):
                # NOTE: Get random one every time
                node_datasource = self.node_datasource
                block = await node_datasource.get_block_by_level(level)
                if block is None:
                    raise FrameworkException(f'Block {level} not found')
                level_logs = await node_datasource.get_logs(
                    {
                        # TODO: Filter by addresses too
                        'fromBlock': hex(level),
                        'toBlock': hex(level),
                    }
                )
                parsed_level_logs = tuple(EvmNodeLogData.from_json(log) for log in level_logs)
                await self._process_level_events(parsed_level_logs, self.topics, sync_level)

        else:
            sync_level = subsquid_sync_level
            fetcher = self._create_fetcher(first_level, sync_level)

            async for _level, events in fetcher.fetch_by_level():
                await self._process_level_events(events, self.topics, sync_level)

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
        topics: dict[str, dict[str, str]],
        sync_level: int,
    ) -> None:
        if not events:
            return

        batch_level = events[0].level
        metrics and metrics.inc(f'{self.name}:events_total', len(events))
        index_level = self.state.level
        if batch_level <= index_level:
            raise FrameworkException(f'Batch level is lower than index level: {batch_level} <= {index_level}')

        self._logger.debug('Processing contract events of level %s', batch_level)
        started_at = time.time()
        matched_handlers = match_events(self._ctx.package, self._config.handlers, events, self.topics)
        metrics and metrics.inc(f'{self.name}:events_matched', len(matched_handlers))
        metrics and metrics.inc(f'{self.name}:time_in_matcher', (time.time() - started_at) / 60)

        if not matched_handlers:
            await self._update_state(level=batch_level)
            return

        started_at = time.time()
        async with self._ctx.transactions.in_transaction(batch_level, sync_level, self.name):
            for handler_config, event in matched_handlers:
                handler_started_at = time.time()
                await self._call_matched_handler(handler_config, event)
                metrics and metrics.inc(
                    f'{self.name}:time_in_callbacks:{handler_config.name}',
                    (time.time() - handler_started_at) / 60,
                )
            await self._update_state(level=batch_level)
        metrics and metrics.inc(f'{self.name}:time_in_callbacks', (time.time() - started_at) / 60)

    async def _call_matched_handler(
        self,
        handler_config: SubsquidEventsHandlerConfig,
        event: SubsquidEvent[Any],
    ) -> None:
        if isinstance(handler_config, SubsquidEventsHandlerConfig) != isinstance(event, SubsquidEvent):
            raise FrameworkException(f'Invalid handler config and event types: {handler_config}, {event}')

        if not handler_config.parent:
            raise ConfigInitializationException

        await self._ctx.fire_handler(
            handler_config.callback,
            handler_config.parent.name,
            self.datasource,
            None,
            event,
        )
