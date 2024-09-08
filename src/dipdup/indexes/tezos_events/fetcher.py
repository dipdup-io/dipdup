from __future__ import annotations

from typing import TYPE_CHECKING

from dipdup.indexes.tezos_tzkt import TezosTzktFetcher
from dipdup.models.tezos import TezosEventData

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from dipdup.datasources.tezos_tzkt import TezosTzktDatasource


class EventFetcher(TezosTzktFetcher[TezosEventData]):
    def __init__(
        self,
        name: str,
        datasources: tuple[TezosTzktDatasource, ...],
        first_level: int,
        last_level: int,
        event_addresses: set[str],
        event_tags: set[str],
    ) -> None:
        super().__init__(name, datasources, first_level, last_level)
        self._event_addresses = event_addresses
        self._event_tags = event_tags

    async def fetch_by_level(self) -> AsyncGenerator[tuple[int, tuple[TezosEventData, ...]], None]:
        event_iter = self.random_datasource.iter_events(
            self._event_addresses,
            self._event_tags,
            self._first_level,
            self._last_level,
        )
        async for level, batch in self.readahead_by_level(event_iter):
            yield level, batch
