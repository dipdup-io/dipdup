from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from dipdup.fetcher import DataFetcher
from dipdup.fetcher import readahead_by_level
from dipdup.models.tezos_tzkt import TzktTokenTransferData

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from dipdup.datasources.tezos_tzkt import TzktDatasource


class TokenTransferFetcher(DataFetcher[TzktTokenTransferData]):
    _datasource: TzktDatasource

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
        self._logger = logging.getLogger('dipdup.fetcher')
        self._token_addresses = token_addresses
        self._token_ids = token_ids
        self._from_addresses = from_addresses
        self._to_addresses = to_addresses

    async def fetch_by_level(self) -> AsyncIterator[tuple[int, tuple[TzktTokenTransferData, ...]]]:
        token_transfer_iter = self._datasource.iter_token_transfers(
            self._token_addresses,
            self._token_ids,
            self._from_addresses,
            self._to_addresses,
            self._first_level,
            self._last_level,
        )
        async for level, batch in readahead_by_level(token_transfer_iter, limit=5_000):
            yield level, batch
