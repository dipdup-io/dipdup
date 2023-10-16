from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from dipdup.fetcher import DataFetcher
from dipdup.fetcher import readahead_by_level
from dipdup.models.tezos_tzkt import TzktTokenBalanceData

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from dipdup.datasources.tezos_tzkt import TzktDatasource


class TokenBalanceFetcher(DataFetcher[TzktTokenBalanceData]):
    _datasource: TzktDatasource

    def __init__(
        self,
        datasource: TzktDatasource,
        token_addresses: set[str],
        token_ids: set[int],
        first_level: int,
        last_level: int,
    ) -> None:
        super().__init__(datasource, first_level, last_level)
        self._logger = logging.getLogger('dipdup.fetcher')
        self._token_addresses = token_addresses
        self._token_ids = token_ids

    async def fetch_by_level(self) -> AsyncIterator[tuple[int, tuple[TzktTokenBalanceData, ...]]]:
        token_balance_iter = self._datasource.iter_token_balances(
            self._token_addresses,
            self._token_ids,
            self._first_level,
            self._last_level,
        )
        async for level, batch in readahead_by_level(token_balance_iter, limit=5_000):
            yield level, batch
