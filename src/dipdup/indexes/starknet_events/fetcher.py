import random
import time
from collections import defaultdict
from collections.abc import AsyncIterator
from typing import Any

from starknet_py.net.client_models import EmittedEvent

from dipdup.datasources.starknet_node import StarknetNodeDatasource
from dipdup.datasources.starknet_subsquid import StarknetSubsquidDatasource
from dipdup.exceptions import FrameworkException
from dipdup.fetcher import readahead_by_level
from dipdup.indexes.starknet_node import StarknetNodeFetcher
from dipdup.indexes.starknet_subsquid import StarknetSubsquidFetcher
from dipdup.models.starknet import StarknetEventData
from dipdup.models.starknet_subsquid import EventRequest

STARKNET_SUBSQUID_READAHEAD_LIMIT = 10000


STARKNET_NODE_READAHEAD_LIMIT = 100
MIN_BATCH_SIZE = 10
MAX_BATCH_SIZE = 10000
BATCH_SIZE_UP = 1.1
BATCH_SIZE_DOWN = 0.5


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


class StarknetNodeEventFetcher(StarknetNodeFetcher[StarknetEventData]):
    def __init__(
        self,
        datasources: tuple[StarknetSubsquidDatasource, ...],
        first_level: int,
        last_level: int,
        event_ids: dict[str, set[str]],
    ) -> None:
        super().__init__(datasources, first_level, last_level)
        self._event_ids = event_ids

    _datasource: StarknetNodeDatasource

    async def fetch_by_level(self) -> AsyncIterator[tuple[int, tuple[StarknetEventData, ...]]]:
        event_iter = self._fetch_by_level()
        async for level, batch in readahead_by_level(event_iter, limit=STARKNET_NODE_READAHEAD_LIMIT):
            yield level, batch

    async def _fetch_by_level(self) -> AsyncIterator[tuple[StarknetEventData, ...]]:
        batch_size = MIN_BATCH_SIZE
        batch_first_level = self._first_level
        ratelimited: bool = False

        while batch_first_level <= self._last_level:
            node = self.random_datasource
            batch_size = self.get_next_batch_size(batch_size, ratelimited)
            ratelimited = False

            started = time.time()

            batch_last_level = min(
                batch_first_level + batch_size,
                self._last_level,
            )
            event_batch = await self.get_events_batch(
                batch_first_level,
                batch_last_level,
                node,
            )

            finished = time.time()
            if finished - started >= node._http_config.ratelimit_sleep:
                ratelimited = True

            for _level, level_events in event_batch.items():
                if not level_events:
                    continue

                parsed_level_events = tuple(StarknetEventData.from_node_json(event.__dict__) for event in level_events)

                yield parsed_level_events

            batch_first_level = batch_last_level + 1

    async def get_events_batch(
        self,
        first_level: int,
        last_level: int,
        node: StarknetNodeDatasource | None = None,
    ) -> dict[int, list[EmittedEvent]]:
        grouped_events: defaultdict[int, list[dict[str, Any]]] = defaultdict(list)
        node = node or self.get_random_node()
        for address, ids in self._event_ids.items():
            logs = await node.get_events(
                address=address,
                keys=[[id] for id in ids],
                first_level=first_level,
                last_level=last_level,
            )
            for log in logs.events:
                grouped_events[log.block_number].append(log)
        return grouped_events

    def get_random_node(self) -> StarknetNodeDatasource:
        if not self._datasources:
            raise FrameworkException('A node datasource requested, but none attached to this index')
        return random.choice(self._datasources)
