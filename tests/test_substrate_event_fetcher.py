from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest

from dipdup.indexes.substrate_events.fetcher import SubstrateNodeEventFetcher
from dipdup.models.substrate import SubstrateEventData


class DummyEvent:
    def __init__(self, idx):  # type: ignore[no-untyped-def]
        self.idx = idx


class DummyHeader(dict):  # type: ignore[type-arg]
    def __init__(self, hash_):  # type: ignore[no-untyped-def]
        super().__init__()
        self['hash'] = hash_


@pytest.mark.asyncio
async def test_substrate_node_event_fetcher():  # type: ignore[no-untyped-def]
    # Mock node datasource
    node = MagicMock()
    node._http_config.batch_size = 2
    node.get_block_hash = AsyncMock(side_effect=lambda level: f'hash_{level}')
    node.get_block_header = AsyncMock(side_effect=lambda hash_: DummyHeader(hash_))  # type: ignore[no-untyped-call]
    node.get_events = AsyncMock(side_effect=lambda hash_: [DummyEvent(hash_ + '_e1'), DummyEvent(hash_ + '_e2')])  # type: ignore[no-untyped-call]

    # Patch get_random_node to return our mock
    class TestFetcher(SubstrateNodeEventFetcher):
        def get_random_node(self):  # type: ignore[no-untyped-def]
            return node

    fetcher = TestFetcher(
        name='test',
        datasources=(node,),
        first_level=1,
        last_level=3,
    )

    # Patch SubstrateEventData.from_node to just return event.idx for test
    orig_from_node = SubstrateEventData.from_node
    SubstrateEventData.from_node = staticmethod(lambda event, header: (event.idx, header['hash']))  # type: ignore[assignment,method-assign]

    results = []
    async for events in fetcher.fetch_events():
        results.append(events)

    # Restore original
    SubstrateEventData.from_node = orig_from_node  # type: ignore[method-assign]

    # There should be 3 levels, each with 2 events
    assert len(results) == 3
    for i, events in enumerate(results, 1):
        assert events == ((f'hash_{i}_e1', f'hash_{i}'), (f'hash_{i}_e2', f'hash_{i}'))  # type: ignore[comparison-overlap]
