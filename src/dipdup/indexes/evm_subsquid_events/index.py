from collections import deque
from collections.abc import Iterable
from typing import Any

from dipdup.config.evm_subsquid_events import SubsquidEventsHandlerConfig
from dipdup.config.evm_subsquid_events import SubsquidEventsIndexConfig
from dipdup.context import DipDupContext
from dipdup.datasources.evm_subsquid import SubsquidDatasource
from dipdup.exceptions import ConfigInitializationException
from dipdup.exceptions import FrameworkException
from dipdup.indexes.evm_subsquid import SubsquidIndex
from dipdup.indexes.evm_subsquid_events.fetcher import EvmNodeEventFetcher
from dipdup.indexes.evm_subsquid_events.fetcher import SubsquidEventFetcher
from dipdup.indexes.evm_subsquid_events.matcher import match_events
from dipdup.models import RollbackMessage
from dipdup.models.evm_node import EvmNodeLogData
from dipdup.models.evm_subsquid import SubsquidEvent
from dipdup.models.evm_subsquid import SubsquidEventData
from dipdup.models.evm_subsquid import SubsquidMessageType
from dipdup.prometheus import Metrics

QueueItem = tuple[EvmNodeLogData, ...] | RollbackMessage


class SubsquidEventsIndex(
    SubsquidIndex[SubsquidEventsIndexConfig, QueueItem, SubsquidDatasource],
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

    async def _synchronize_subsquid(self, sync_level: int) -> None:
        first_level = self.state.level + 1
        fetcher = self._create_subsquid_fetcher(first_level, sync_level)

        async for _level, events in fetcher.fetch_by_level():
            await self._process_level_data(events, sync_level)
            Metrics.set_sqd_processor_last_block(_level)

    async def _synchronize_node(self, sync_level: int) -> None:
        first_level = self.state.level + 1
        fetcher = self._create_node_fetcher(first_level, sync_level)

        async for _level, events in fetcher.fetch_by_level():
            await self._process_level_data(events, sync_level)
            Metrics.set_sqd_processor_last_block(_level)

    def _create_subsquid_fetcher(self, first_level: int, last_level: int) -> SubsquidEventFetcher:
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

        return SubsquidEventFetcher(
            datasource=self._datasource,
            first_level=first_level,
            last_level=last_level,
            topics=tuple(topics),
        )

    def _create_node_fetcher(self, first_level: int, last_level: int) -> EvmNodeEventFetcher:
        return EvmNodeEventFetcher(
            datasources=self.node_datasources,
            first_level=first_level,
            last_level=last_level,
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
