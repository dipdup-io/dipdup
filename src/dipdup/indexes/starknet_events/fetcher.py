import random
from collections.abc import AsyncIterator
from typing import Any

from dipdup.datasources.starknet_node import StarknetNodeDatasource
from dipdup.datasources.starknet_subsquid import StarknetSubsquidDatasource
from dipdup.exceptions import FrameworkException
from dipdup.fetcher import FetcherChannel
from dipdup.fetcher import readahead_by_level
from dipdup.indexes.starknet_node import StarknetNodeFetcher
from dipdup.indexes.starknet_subsquid import StarknetSubsquidFetcher
from dipdup.models.starknet import StarknetEventData
from dipdup.models.starknet_subsquid import EventRequest

STARKNET_NODE_READAHEAD_LIMIT = 100
STARKNET_SUBSQUID_READAHEAD_LIMIT = 10000


class StarknetSubsquidEventFetcher(StarknetSubsquidFetcher[StarknetEventData]):
    def __init__(
        self,
        datasources: tuple[StarknetSubsquidDatasource, ...],
        first_level: int,
        last_level: int,
        event_ids: dict[str, set[str]],
    ) -> None:
        super().__init__(datasources, first_level, last_level)
        self._event_ids = event_ids

    async def fetch_by_level(self) -> AsyncIterator[tuple[int, tuple[StarknetEventData, ...]]]:
        filters: tuple[EventRequest, ...] = tuple(
            {
                'key0': list(ids),
                'fromAddress': [address],
            }
            for address, ids in self._event_ids.items()
        )
        event_iter = self.random_datasource.iter_events(
            first_level=self._first_level,
            last_level=self._last_level,
            filters=filters,
        )
        async for level, batch in readahead_by_level(event_iter, limit=STARKNET_SUBSQUID_READAHEAD_LIMIT):
            yield level, batch


class EventFetcherChannel(FetcherChannel[StarknetEventData, StarknetNodeDatasource, tuple[str, tuple[str, ...]]]):

    _offset: str | None

    async def fetch(self) -> None:
        address, key0s = next(iter(self._filter))
        events_chunk = await self._datasources[0].get_events(
            address=address,
            keys=[list(key0s), [], []],
            first_level=self._first_level,
            last_level=self._last_level,
            continuation_token=self._offset or None,
        )

        for event in events_chunk.events:
            self._buffer[event.block_number].append(StarknetEventData.from_node_json(event.__dict__))

        if events_chunk.continuation_token:
            self._offset = events_chunk.continuation_token
            if events_chunk.events:
                self._head = events_chunk.events[-1].block_number
        else:
            self._head = self._last_level
            self._offset = None


class StarknetNodeEventFetcher(StarknetNodeFetcher[StarknetEventData]):
    def __init__(
        self,
        datasources: tuple[StarknetNodeDatasource, ...],
        first_level: int,
        last_level: int,
        event_ids: dict[str, set[str]],
    ) -> None:
        super().__init__(datasources, first_level, last_level)
        self._event_ids = event_ids

    async def fetch_by_level(self) -> AsyncIterator[tuple[int, tuple[StarknetEventData, ...]]]:
        channels: set[FetcherChannel[Any, Any, Any]] = set()
        for address, key0s in self._event_ids.items():
            filter = set()
            filter.add((address, tuple(key0s)))
            channel = EventFetcherChannel(
                buffer=self._buffer,
                filter=filter,
                first_level=self._first_level,
                last_level=self._last_level,
                # NOTE: Fixed datasource to use continuation token
                datasources=(self.get_random_node(),),
            )
            channels.add(channel)

        events_iter = self._merged_iter(
            channels, lambda i: tuple(sorted(i, key=lambda x: f'{x.block_number}_{x.transaction_index}'))
        )
        async for level, batch in readahead_by_level(events_iter, limit=STARKNET_NODE_READAHEAD_LIMIT):
            yield level, batch

    def get_random_node(self) -> StarknetNodeDatasource:
        if not self._datasources:
            raise FrameworkException('A node datasource requested, but none attached to this index')
        return random.choice(self._datasources)
