from __future__ import annotations

from typing import TYPE_CHECKING

from dipdup.indexes.tezos_tzkt import TezosTzktFetcher
from dipdup.models.tezos import TezosTokenTransferData

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from dipdup.datasources.tezos_tzkt import TezosTzktDatasource


class TokenTransferFetcher(TezosTzktFetcher[TezosTokenTransferData]):

    def __init__(
        self,
        name: str,
        datasources: tuple[TezosTzktDatasource, ...],
        token_addresses: set[str],
        token_ids: set[int],
        from_addresses: set[str],
        to_addresses: set[str],
        first_level: int,
        last_level: int,
    ) -> None:
        super().__init__(
            name=name,
            datasources=datasources,
            first_level=first_level,
            last_level=last_level,
        )
        self._token_addresses = token_addresses
        self._token_ids = token_ids
        self._from_addresses = from_addresses
        self._to_addresses = to_addresses

    async def fetch_by_level(self) -> AsyncIterator[tuple[int, tuple[TezosTokenTransferData, ...]]]:
        token_transfer_iter = self.random_datasource.iter_token_transfers(
            self._token_addresses,
            self._token_ids,
            self._from_addresses,
            self._to_addresses,
            self._first_level,
            self._last_level,
        )
        async for level, batch in self.readahead_by_level(token_transfer_iter):
            yield level, batch
