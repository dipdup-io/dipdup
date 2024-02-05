import asyncio
import random
import time
from collections import defaultdict
from collections import deque
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
from dipdup.prometheus import Metrics

LEVEL_BATCH_TIMEOUT = 1
NODE_SYNC_LIMIT = 128


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
    def random_node(self) -> EvmNodeDatasource:
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
        logs_by_level: dict[int, list[EvmNodeLogData]] = defaultdict(list)

        # NOTE: Drain queue and group messages by level.
        while True:
            while self._queue:
                logs = self._queue.popleft()
                message_level = logs.level
                if message_level <= self.state.level:
                    self._logger.debug('Skipping outdated message: %s <= %s', message_level, self.state.level)
                    continue

                logs_by_level[message_level].append(logs)

            # NOTE: Wait for more messages a bit more - node doesn't notify us about the level boundaries.
            await asyncio.sleep(LEVEL_BATCH_TIMEOUT)
            if not self._queue:
                break

        for message_level, level_logs in logs_by_level.items():
            self._logger.info('Processing %s event logs of level %s', len(level_logs), message_level)
            await self._process_level_events(tuple(level_logs), message_level)
            Metrics.set_sqd_processor_last_block(message_level)

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
        Metrics.set_sqd_processor_chain_height(subsquid_sync_level)

        use_node = False
        if self.node_datasources:
            node_sync_level = await self.random_node.get_head_level()
            subsquid_lag = abs(node_sync_level - subsquid_sync_level)
            subsquid_available = subsquid_sync_level - index_level
            self._logger.info('Subsquid is %s levels behind; %s available', subsquid_lag, subsquid_available)
            if subsquid_available < NODE_SYNC_LIMIT:
                use_node = True
            elif self._config.node_only:
                self._logger.debug('Using node anyway')
                use_node = True

        # NOTE: Fetch last blocks from node if there are not enough realtime messages in queue
        if use_node and self.node_datasources:
            sync_level = min(sync_level, node_sync_level)
            self._logger.debug('Using node datasource; sync level: %s', sync_level)
            topics = set()
            for handler in self._config.handlers:
                typename = handler.contract.module_name
                topics.add(self.topics[typename][handler.name])

            # NOTE: Requesting logs by batches of `http.batch_size`
            evm_node: EvmNodeDatasource = self.random_node
            batch_size = evm_node._http_config.batch_size

            batch_first_level = first_level
            while batch_first_level <= sync_level:
                # NOTE: We need block timestamps for each level, so fetch them separately and match with logs.
                timestamps: dict[int, int] = {}
                tasks: deque[asyncio.Task[Any]] = deque()

                batch_last_level = min(batch_first_level + batch_size, sync_level)
                level_logs_task = asyncio.create_task(
                    self.random_node.get_logs(
                        {
                            'fromBlock': hex(batch_first_level),
                            'toBlock': hex(batch_last_level),
                        }
                    )
                )

                async def _fetch_timestamp(level: int, timestamps: dict[int, int]) -> None:
                    block = await self.random_node.get_block_by_level(level)
                    timestamps[level] = int(block['timestamp'], 16)

                level = batch_last_level
                level_logs = await level_logs_task
                for level in {int(log['blockNumber'], 16) for log in level_logs}:
                    tasks.append(
                        asyncio.create_task(
                            _fetch_timestamp(level, timestamps),
                            name=f'last_mile:{level}',
                        ),
                    )

                await asyncio.gather(*tasks)

                parsed_level_logs = tuple(
                    EvmNodeLogData.from_json(
                        log,
                        timestamps[int(log['blockNumber'], 16)],
                    )
                    for log in level_logs
                )

                await self._process_level_events(parsed_level_logs, sync_level)
                Metrics.set_sqd_processor_last_block(level)

                batch_first_level = batch_last_level + 1
        else:
            sync_level = min(sync_level, subsquid_sync_level)
            fetcher = self._create_fetcher(first_level, sync_level)

            async for _level, events in fetcher.fetch_by_level():
                await self._process_level_events(events, sync_level)
                Metrics.set_sqd_processor_last_block(_level)

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
