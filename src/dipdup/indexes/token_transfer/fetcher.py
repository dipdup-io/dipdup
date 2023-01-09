from __future__ import annotations

import logging
from typing import AsyncIterator

from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.fetcher import DataFetcher
from dipdup.fetcher import yield_by_level
from dipdup.models import TokenTransferData


class TokenTransferFetcher(DataFetcher[TokenTransferData]):
    def __init__(
        self,
        datasource: TzktDatasource,
        token_addresses: set[str],
        token_ids: set[int],
        from_addresses: set[str],
        to_addresses: set[str],
        first_level: int,
        last_level: int,
    ) -> None:
        super().__init__(datasource, first_level, last_level)
        self._logger = logging.getLogger('dipdup.tzkt')
        self._token_addresses = token_addresses
        self._token_ids = token_ids
        self._from_addresses = from_addresses
        self._to_addresses = to_addresses

    async def fetch_by_level(self) -> AsyncIterator[tuple[int, tuple[TokenTransferData, ...]]]:
        token_transfer_iter = self._datasource.iter_token_transfers(
            self._token_addresses,
            self._token_ids,
            self._from_addresses,
            self._to_addresses,
            self._first_level,
            self._last_level,
        )
        async for level, batch in yield_by_level(token_transfer_iter):
            yield level, batch
