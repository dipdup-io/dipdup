from collections import deque
from collections.abc import Iterable
from typing import TYPE_CHECKING
from typing import Any

from dipdup.config.evm_events import EvmEventsHandlerConfig
from dipdup.config.evm_events import EvmEventsIndexConfig
from dipdup.datasources.evm_node import EvmNodeDatasource
from dipdup.datasources.evm_subsquid import EvmSubsquidDatasource
from dipdup.exceptions import ConfigInitializationException
from dipdup.exceptions import FrameworkException
from dipdup.indexes.evm import EvmIndex
from dipdup.indexes.evm_events.fetcher import EvmNodeEventFetcher
from dipdup.indexes.evm_events.fetcher import EvmSubsquidEventFetcher
from dipdup.indexes.evm_events.matcher import match_events
from dipdup.models import RollbackMessage
from dipdup.models.evm import EvmEvent
from dipdup.models.evm import EvmEventData
from dipdup.models.subsquid import SubsquidMessageType
from dipdup.prometheus import Metrics

QueueItem = tuple[EvmEventData, ...] | RollbackMessage
EvmDatasource = EvmSubsquidDatasource | EvmNodeDatasource

if TYPE_CHECKING:
    from dipdup.context import DipDupContext


class EvmEventsIndex(
    EvmIndex[EvmEventsIndexConfig, QueueItem, EvmDatasource],
    message_type=SubsquidMessageType.logs,
):
    def __init__(
        self,
        ctx: 'DipDupContext',
        config: EvmEventsIndexConfig,
        datasources: tuple[EvmDatasource, ...],
    ) -> None:
        super().__init__(ctx, config, datasources)
        self._event_abis = {
            handler.contract.module_name: self._ctx.package.get_converted_evm_abi(handler.contract.module_name)[
                'events'
            ]
            for handler in self._config.handlers
        }

    async def _synchronize_subsquid(self, sync_level: int) -> None:
        first_level = self.state.level + 1
        fetcher = self._create_subsquid_fetcher(first_level, sync_level)

        async for _level, logs in fetcher.fetch_by_level():
            await self._process_level_data(logs, sync_level)
            Metrics.set_sqd_processor_last_block(_level)

    async def _synchronize_node(self, sync_level: int) -> None:
        first_level = self.state.level + 1
        fetcher = self._create_node_fetcher(first_level, sync_level)

        async for _level, logs in fetcher.fetch_by_level():
            await self._process_level_data(logs, sync_level)
            Metrics.set_sqd_processor_last_block(_level)

    def _create_subsquid_fetcher(self, first_level: int, last_level: int) -> EvmSubsquidEventFetcher:
        addresses = set()
        topics: deque[tuple[str | None, str]] = deque()

        for handler_config in self._config.handlers:
            address = handler_config.contract.address
            if address is not None:
                addresses.add(address)
            elif handler_config.contract.abi is None:
                raise NotImplementedError('Either contract address or ABI must be specified')

            event_abi = self._ctx.package.get_converted_evm_abi(handler_config.contract.module_name)['events'][
                handler_config.name
            ]
            topics.append((address, event_abi['topic0']))

        if not self.subsquid_datasources:
            raise FrameworkException('Creating EvmSubsquidEventFetcher, but no `evm.subsquid` datasources available')

        return EvmSubsquidEventFetcher(
            datasources=self.subsquid_datasources,
            first_level=first_level,
            last_level=last_level,
            topics=tuple(topics),
        )

    def _create_node_fetcher(self, first_level: int, last_level: int) -> EvmNodeEventFetcher:
        if not self.node_datasources:
            raise FrameworkException('Creating EvmNodeEventFetcher, but no `evm.node` datasources available')

        return EvmNodeEventFetcher(
            datasources=self.node_datasources,
            first_level=first_level,
            last_level=last_level,
        )

    def _match_level_data(
        self,
        handlers: tuple[EvmEventsHandlerConfig, ...],
        level_data: Iterable[EvmEventData],
    ) -> deque[Any]:
        return match_events(self._ctx.package, handlers, level_data, self._event_abis)

    async def _call_matched_handler(
        self,
        handler_config: EvmEventsHandlerConfig,
        event: EvmEvent[Any],
    ) -> None:

        if not handler_config.parent:
            raise ConfigInitializationException

        await self._ctx.fire_handler(
            handler_config.callback,
            handler_config.parent.name,
            None,
            event,
        )
