from contextlib import ExitStack

from dipdup.config import TokenTransferHandlerConfig
from dipdup.config import TokenTransferIndexConfig
from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.enums import MessageType
from dipdup.exceptions import ConfigInitializationException
from dipdup.exceptions import FrameworkException
from dipdup.index import Index
from dipdup.index import extract_level
from dipdup.indexes.token_transfer.fetcher import TokenTransferFetcher
from dipdup.indexes.token_transfer.matcher import match_token_transfers
from dipdup.models import TokenTransferData
from dipdup.prometheus import Metrics

TokenTransferQueueItem = tuple[TokenTransferData, ...]


class TokenTransferIndex(
    Index[TokenTransferIndexConfig, TokenTransferQueueItem, TzktDatasource],
    message_type=MessageType.token_transfer,
):
    def push_token_transfers(self, token_transfers: TokenTransferQueueItem) -> None:
        self.push_realtime_message(token_transfers)

    def _create_fetcher(self, first_level: int, last_level: int) -> TokenTransferFetcher:
        token_addresses: set[str] = set()
        token_ids: set[int] = set()
        from_addresses: set[str] = set()
        to_addresses: set[str] = set()
        for handler_config in self._config.handlers:
            if handler_config.contract:
                token_addresses.add(handler_config.contract.get_address())
            if handler_config.token_id is not None:
                token_ids.add(handler_config.token_id)
            if handler_config.from_:
                from_addresses.add(handler_config.from_.get_address())
            if handler_config.to:
                to_addresses.add(handler_config.to.get_address())

        return TokenTransferFetcher(
            datasource=self._datasource,
            token_addresses=token_addresses,
            token_ids=token_ids,
            from_addresses=from_addresses,
            to_addresses=to_addresses,
            first_level=first_level,
            last_level=last_level,
        )

    async def _synchronize(self, sync_level: int) -> None:
        """Fetch token transfers via Fetcher and pass to message callback"""
        index_level = await self._enter_sync_state(sync_level)
        if index_level is None:
            return

        first_level = index_level + 1
        self._logger.info('Fetching token transfers from level %s to %s', first_level, sync_level)
        fetcher = self._create_fetcher(first_level, sync_level)

        async for level, token_transfers in fetcher.fetch_by_level():
            with ExitStack() as stack:
                if Metrics.enabled:
                    Metrics.set_levels_to_sync(self._config.name, sync_level - level)
                    stack.enter_context(Metrics.measure_level_sync_duration())
                await self._process_level_token_transfers(token_transfers, sync_level)

        await self._exit_sync_state(sync_level)

    async def _process_level_token_transfers(
        self,
        token_transfers: tuple[TokenTransferData, ...],
        sync_level: int,
    ) -> None:
        if not token_transfers:
            return

        batch_level = extract_level(token_transfers)
        index_level = self.state.level
        if batch_level <= index_level:
            raise FrameworkException(f'Batch level is lower than index level: {batch_level} <= {index_level}')

        self._logger.debug('Processing token transfers of level %s', batch_level)
        matched_handlers = match_token_transfers(self._config.handlers, token_transfers)

        if Metrics.enabled:
            Metrics.set_index_handlers_matched(len(matched_handlers))

        # NOTE: We still need to bump index level but don't care if it will be done in existing transaction
        if not matched_handlers:
            await self.state.update_status(level=batch_level)
            return

        async with self._ctx._transactions.in_transaction(batch_level, sync_level, self.name):
            for handler_config, token_transfer in matched_handlers:
                await self._call_matched_handler(handler_config, token_transfer)
            await self.state.update_status(level=batch_level)

    async def _call_matched_handler(
        self, handler_config: TokenTransferHandlerConfig, token_transfer: TokenTransferData
    ) -> None:
        if not handler_config.parent:
            raise ConfigInitializationException

        await self._ctx._fire_handler(
            handler_config.callback,
            handler_config.parent.name,
            self.datasource,
            # NOTE: missing `operation_id` field in API to identify operation
            None,
            token_transfer,
        )

    async def _process_queue(self) -> None:
        """Process WebSocket queue"""
        if self._queue:
            self._logger.debug('Processing websocket queue')
        while self._queue:
            token_transfers = self._queue.popleft()
            message_level = token_transfers[0].level
            if message_level <= self.state.level:
                self._logger.debug('Skipping outdated message: %s <= %s', message_level, self.state.level)
                continue

            with ExitStack() as stack:
                if Metrics.enabled:
                    stack.enter_context(Metrics.measure_level_realtime_duration())
                await self._process_level_token_transfers(token_transfers, message_level)
