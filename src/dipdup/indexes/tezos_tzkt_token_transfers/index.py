from collections import deque
from typing import Any

from dipdup.config.tezos_tzkt_token_transfers import TzktTokenTransfersHandlerConfig
from dipdup.config.tezos_tzkt_token_transfers import TzktTokenTransfersIndexConfig
from dipdup.exceptions import ConfigInitializationException
from dipdup.indexes.tezos_tzkt import TzktIndex
from dipdup.indexes.tezos_tzkt_token_transfers.fetcher import TokenTransferFetcher
from dipdup.indexes.tezos_tzkt_token_transfers.matcher import match_token_transfers
from dipdup.models.tezos_tzkt import TzktMessageType
from dipdup.models.tezos_tzkt import TzktRollbackMessage
from dipdup.models.tezos_tzkt import TzktTokenTransferData

TokenTransferQueueItem = tuple[TzktTokenTransferData, ...] | TzktRollbackMessage


class TzktTokenTransfersIndex(
    TzktIndex[TzktTokenTransfersIndexConfig, TokenTransferQueueItem],
    message_type=TzktMessageType.token_transfer,
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

        async for _, token_transfers in fetcher.fetch_by_level():
            await self._process_level_data(token_transfers, sync_level)

        await self._exit_sync_state(sync_level)

    async def _call_matched_handler(
        self, handler_config: TzktTokenTransfersHandlerConfig, token_transfer: TzktTokenTransferData
    ) -> None:
        if not handler_config.parent:
            raise ConfigInitializationException

        await self._ctx.fire_handler(
            handler_config.callback,
            handler_config.parent.name,
            self.datasource,
            # NOTE: missing `operation_id` field in API to identify operation
            None,
            token_transfer,
        )

    def _match_level_data(self, handlers: Any, level_data: Any) -> deque[Any]:
        return match_token_transfers(handlers, level_data)
