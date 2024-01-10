import asyncio
from collections import defaultdict
from collections import deque
from collections.abc import Iterable
from typing import Any

from dipdup.config.evm_subsquid_events import SubsquidEventsHandlerConfig
from dipdup.config.evm_subsquid_events import SubsquidEventsIndexConfig
from dipdup.context import DipDupContext
from dipdup.datasources.evm_subsquid import SubsquidDatasource
from dipdup.exceptions import ConfigInitializationException
from dipdup.exceptions import FrameworkException
from dipdup.indexes.evm_subsquid import NODE_BATCH_SIZE
from dipdup.indexes.evm_subsquid import NODE_LEVEL_TIMEOUT
from dipdup.indexes.evm_subsquid import SubsquidIndex
from dipdup.indexes.evm_subsquid_events.fetcher import EventLogFetcher
from dipdup.indexes.evm_subsquid_events.matcher import match_events
from dipdup.models.evm_node import EvmNodeLogData
from dipdup.models.evm_subsquid import SubsquidEvent
from dipdup.models.evm_subsquid import SubsquidEventData
from dipdup.models.evm_subsquid import SubsquidMessageType
from dipdup.prometheus import Metrics


class SubsquidEventsIndex(
    SubsquidIndex[SubsquidEventsIndexConfig, EvmNodeLogData, SubsquidDatasource],
    message_type=SubsquidMessageType.logs,
):
    def __init__(
        self,
        ctx: DipDupContext,
        config: SubsquidEventsIndexConfig,
        datasource: SubsquidDatasource,
    ) -> None:
        super().__init__(ctx, config, datasource)
        self._topics: dict[str, dict[str, str]] | None = None

    @property
    def topics(self) -> dict[str, dict[str, str]]:
        if self._topics is None:
            self._topics = {}
            for handler_config in self._config.handlers:
                typename = handler_config.contract.module_name
                event_abi = self._ctx.package.get_converted_abi(typename)['events']
                self._topics[typename] = {k: v['topic0'] for k, v in event_abi.items()}

        return self._topics

    async def _process_queue(self) -> None:
        logs_by_level = defaultdict(list)

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
            await asyncio.sleep(NODE_LEVEL_TIMEOUT)
            if not self._queue:
                break

        for message_level, level_logs in logs_by_level.items():
            self._logger.info('Processing %s event logs of level %s', len(level_logs), message_level)
            await self._process_level_data(tuple(level_logs), message_level)
            Metrics.set_sqd_processor_last_block(message_level)

    async def _synchronize_subsquid(self, sync_level: int) -> None:
        first_level = self.state.level + 1
        fetcher = self._create_fetcher(first_level, sync_level)

        async for _level, events in fetcher.fetch_by_level():
            await self._process_level_data(events, sync_level)
            Metrics.set_sqd_processor_last_block(_level)

    async def _synchronize_node(self, sync_level: int) -> None:
        topics = set()
        for handler in self._config.handlers:
            typename = handler.contract.module_name
            topics.add(self.topics[typename][handler.name])

        # NOTE: Requesting logs by batches of NODE_BATCH_SIZE.
        batch_first_level = self.state.level + 1
        while batch_first_level <= sync_level:
            # NOTE: We need block timestamps for each level, so fetch them separately and match with logs.
            timestamps: dict[int, int] = {}
            tasks: deque[asyncio.Task[Any]] = deque()

            batch_last_level = min(batch_first_level + NODE_BATCH_SIZE, sync_level)
            level_logs_task = asyncio.create_task(
                self.get_random_node().get_logs(
                    {
                        'fromBlock': hex(batch_first_level),
                        'toBlock': hex(batch_last_level),
                    }
                )
            )
            tasks.append(level_logs_task)

            async def _fetch_timestamp(level: int, timestamps: dict[int, int]) -> None:
                block = await self.get_random_node().get_block_by_level(level)
                timestamps[level] = int(block['timestamp'], 16)

            for level in range(batch_first_level, batch_last_level + 1):
                tasks.append(
                    asyncio.create_task(
                        _fetch_timestamp(level, timestamps),
                        name=f'last_mile:{level}',
                    ),
                )

            await asyncio.gather(*tasks)

            level_logs = await level_logs_task
            parsed_level_logs = tuple(
                EvmNodeLogData.from_json(
                    log,
                    timestamps[int(log['blockNumber'], 16)],
                )
                for log in level_logs
            )

            await self._process_level_data(parsed_level_logs, sync_level)
            Metrics.set_sqd_processor_last_block(level)

            batch_first_level = batch_last_level + 1

    def _create_fetcher(self, first_level: int, last_level: int) -> EventLogFetcher:
        addresses = set()
        topics: deque[tuple[str | None, str]] = deque()

        for handler_config in self._config.handlers:
            address = handler_config.contract.address
            if address is not None:
                addresses.add(address)
            elif handler_config.contract.abi is None:
                raise NotImplementedError('Either contract address or ABI must be specified')

            event_abi = self._ctx.package.get_converted_abi(handler_config.contract.module_name)['events'][
                handler_config.name
            ]
            topics.append((address, event_abi['topic0']))

        return EventLogFetcher(
            datasource=self._datasource,
            first_level=first_level,
            last_level=last_level,
            topics=tuple(topics),
        )

    def _match_level_data(
        self,
        handlers: tuple[SubsquidEventsHandlerConfig, ...],
        level_data: Iterable[SubsquidEventData | EvmNodeLogData],
    ) -> deque[Any]:
        return match_events(self._ctx.package, handlers, level_data, self.topics)

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
