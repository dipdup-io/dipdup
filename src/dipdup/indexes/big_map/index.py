from contextlib import ExitStack
from datetime import datetime
from typing import Any

from dipdup.config import BigMapHandlerConfig
from dipdup.config import BigMapIndexConfig
from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.enums import MessageType
from dipdup.enums import SkipHistory
from dipdup.exceptions import ConfigInitializationException
from dipdup.exceptions import ConfigurationError
from dipdup.exceptions import FrameworkException
from dipdup.index import Index
from dipdup.index import extract_level
from dipdup.indexes.big_map.fetcher import BigMapFetcher
from dipdup.indexes.big_map.fetcher import get_big_map_pairs
from dipdup.indexes.big_map.matcher import match_big_maps
from dipdup.models import BigMapAction
from dipdup.models import BigMapData
from dipdup.models import BigMapDiff
from dipdup.prometheus import Metrics

BigMapQueueItem = tuple[BigMapData, ...]


class BigMapIndex(
    Index[BigMapIndexConfig, BigMapQueueItem, TzktDatasource],
    message_type=MessageType.big_map,
):
    def push_big_maps(self, big_maps: BigMapQueueItem) -> None:
        """Push big map diffs to queue"""
        self.push_realtime_message(big_maps)

    async def _process_queue(self) -> None:
        """Process WebSocket queue"""
        if self._queue:
            self._logger.debug('Processing websocket queue')
        while self._queue:
            big_maps = self._queue.popleft()
            message_level = big_maps[0].level
            if message_level <= self.state.level:
                self._logger.debug('Skipping outdated message: %s <= %s', message_level, self.state.level)
                continue

            with ExitStack() as stack:
                if Metrics.enabled:
                    stack.enter_context(Metrics.measure_level_realtime_duration())
                await self._process_level_big_maps(big_maps, message_level)

    async def _synchronize(self, sync_level: int) -> None:
        """Fetch operations via Fetcher and pass to message callback"""
        index_level = await self._enter_sync_state(sync_level)
        if index_level is None:
            return

        if self._config.skip_history == SkipHistory.always:
            await self._synchronize_level(sync_level)
        elif self._config.skip_history == SkipHistory.once and not self.state.level:
            await self._synchronize_level(sync_level)
        else:
            await self._synchronize_full(index_level, sync_level)

        await self._exit_sync_state(sync_level)

    async def _synchronize_full(self, index_level: int, sync_level: int) -> None:
        first_level = index_level + 1
        self._logger.info('Fetching big map diffs from level %s to %s', first_level, sync_level)

        fetcher = BigMapFetcher.create(
            self._config,
            self._datasource,
            first_level,
            sync_level,
        )

        async for level, big_maps in fetcher.fetch_by_level():
            with ExitStack() as stack:
                if Metrics.enabled:
                    Metrics.set_levels_to_sync(self._config.name, sync_level - level)
                    stack.enter_context(Metrics.measure_level_sync_duration())
                await self._process_level_big_maps(big_maps, sync_level)

    async def _synchronize_level(self, head_level: int) -> None:
        # NOTE: Checking late because feature flags could be modified after loading config
        if not self._ctx.config.advanced.early_realtime:
            raise ConfigurationError('`skip_history` requires `early_realtime` feature flag to be enabled')

        big_map_pairs = get_big_map_pairs(self._config.handlers)
        big_map_ids: set[tuple[int, str, str]] = set()

        for address, path in big_map_pairs:
            async for contract_big_maps in self._datasource.iter_contract_big_maps(address):
                for contract_big_map in contract_big_maps:
                    if contract_big_map['path'] == path:
                        big_map_ids.add((int(contract_big_map['ptr']), address, path))

        # NOTE: Do not use `_process_level_big_maps` here; we want to maintain transaction manually.
        async with self._ctx._transactions.in_transaction(head_level, head_level, self.name):
            for big_map_id, address, path in big_map_ids:
                async for big_map_keys in self._datasource.iter_big_map(big_map_id, head_level):
                    big_map_data = tuple(
                        BigMapData(
                            id=big_map_key['id'],
                            level=head_level,
                            operation_id=head_level,
                            timestamp=datetime.now(),
                            bigmap=big_map_id,
                            contract_address=address,
                            path=path,
                            action=BigMapAction.ADD_KEY,
                            active=big_map_key['active'],
                            key=big_map_key['key'],
                            value=big_map_key['value'],
                        )
                        for big_map_key in big_map_keys
                    )
                    matched_handlers = match_big_maps(self._config.handlers, big_map_data)
                    for handler_config, big_map_diff in matched_handlers:
                        await self._call_matched_handler(handler_config, big_map_diff)

            await self.state.update_status(level=head_level)

    async def _process_level_big_maps(
        self,
        big_maps: tuple[BigMapData, ...],
        sync_level: int,
    ) -> None:
        if not big_maps:
            return

        batch_level = extract_level(big_maps)
        index_level = self.state.level
        if batch_level <= index_level:
            raise FrameworkException(f'Batch level is lower than index level: {batch_level} <= {index_level}')

        self._logger.debug('Processing big map diffs of level %s', batch_level)
        matched_handlers = match_big_maps(self._config.handlers, big_maps)

        if Metrics.enabled:
            Metrics.set_index_handlers_matched(len(matched_handlers))

        # NOTE: We still need to bump index level but don't care if it will be done in existing transaction
        if not matched_handlers:
            await self.state.update_status(level=batch_level)
            return

        async with self._ctx._transactions.in_transaction(batch_level, sync_level, self.name):
            for handler_config, big_map_diff in matched_handlers:
                await self._call_matched_handler(handler_config, big_map_diff)
            await self.state.update_status(level=batch_level)

    async def _call_matched_handler(
        self, handler_config: BigMapHandlerConfig, big_map_diff: BigMapDiff[Any, Any]
    ) -> None:
        if not handler_config.parent:
            raise ConfigInitializationException

        await self._ctx._fire_handler(
            handler_config.callback,
            handler_config.parent.name,
            self.datasource,
            # NOTE: missing `operation_id` field in API to identify operation
            None,
            big_map_diff,
        )
