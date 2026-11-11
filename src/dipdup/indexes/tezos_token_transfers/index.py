from collections import deque
from typing import Any

from dipdup.config.tezos_token_transfers import TezosTokenTransfersIndexConfig
from dipdup.indexes.tezos_token_transfers.fetcher import TokenTransferFetcher
from dipdup.indexes.tezos_token_transfers.matcher import match_token_transfers
from dipdup.indexes.tezos_tzkt import TezosIndex
from dipdup.models import RollbackMessage
from dipdup.models.tezos import TezosTokenTransferData
from dipdup.subscriptions.tezos_tzkt import TezosTzktMessageType

QueueItem = tuple[TezosTokenTransferData, ...] | RollbackMessage


class TezosTokenTransfersIndex(
    TezosIndex[TezosTokenTransfersIndexConfig, QueueItem],
    message_type=TezosTzktMessageType.token_transfer,
):
    def _create_fetcher(self, first_level: int, last_level: int) -> TokenTransferFetcher:
        handlers = self._config.handlers
        token_addresses = {h.contract.get_address() for h in handlers if h.contract}
        token_ids = {h.token_id for h in handlers if h.token_id is not None}
        from_addresses = {h.from_.get_address() for h in handlers if h.from_}
        to_addresses = {h.to.get_address() for h in handlers if h.to}

        # NOTE: TzKT combines filters with AND; one is valid only when every handler sets that field
        if not all(h.contract for h in handlers):
            token_addresses = set()
        if not all(h.token_id is not None for h in handlers):
            token_ids = set()
        if not all(h.from_ for h in handlers):
            from_addresses = set()
        if not all(h.to for h in handlers):
            to_addresses = set()

        return TokenTransferFetcher(
            name=self.name,
            datasources=self._datasources,
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

    def _match_level_data(self, handlers: Any, level_data: Any) -> deque[Any]:
        return match_token_transfers(handlers, level_data)
