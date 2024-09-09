from collections import deque
from typing import Any

from dipdup.config.tezos_token_transfers import TezosTokenTransfersIndexConfig
from dipdup.indexes.tezos_token_transfers.fetcher import TokenTransferFetcher
from dipdup.indexes.tezos_token_transfers.matcher import match_token_transfers
from dipdup.indexes.tezos_tzkt import TezosIndex
from dipdup.models import RollbackMessage
from dipdup.models.tezos import TezosTokenTransferData
from dipdup.models.tezos_tzkt import TezosTzktMessageType

QueueItem = tuple[TezosTokenTransferData, ...] | RollbackMessage


class TezosTokenTransfersIndex(
    TezosIndex[TezosTokenTransfersIndexConfig, QueueItem],
    message_type=TezosTzktMessageType.token_transfer,
):
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
