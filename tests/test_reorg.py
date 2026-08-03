"""Reorg stand: replays raw TzKT SignalR frames through the whole realtime pipeline.

Nothing is stubbed below the websocket transport: frames go into
`TezosTzktDatasource._on_message`, which keeps channel levels, buffers messages and emits
head/rollback events to `IndexDispatcher`, which fills the index queue, which the index
drains in FIFO order into a versioned transaction. Only the socket is missing.
"""

from collections.abc import AsyncIterator
from collections.abc import Callable
from contextlib import AsyncExitStack
from typing import Any

import pytest

from dipdup import env
from dipdup.config import DipDupConfig
from dipdup.datasources.tezos_tzkt import TezosTzktDatasource
from dipdup.datasources.tezos_tzkt import TezosTzktMessageAction
from dipdup.index import Index
from dipdup.models import IndexStatus
from dipdup.models import ModelUpdate
from dipdup.performance import queues
from dipdup.subscriptions.tezos_tzkt import HeadSubscription
from dipdup.subscriptions.tezos_tzkt import TezosTzktMessageType
from dipdup.test import create_dummy_dipdup
from dipdup.test import spawn_index
from tests import TEST_CONFIGS

PACKAGE_PATH = TEST_CONFIGS.parent / 'packages' / 'reorg'


def head_frame(action: TezosTzktMessageAction, level: int) -> dict[str, Any]:
    """Raw SignalR frame as TzKT sends it on the `head` channel."""
    frame: dict[str, Any] = {'type': action.value, 'state': level}
    if action == TezosTzktMessageAction.DATA:
        frame['data'] = {
            'chain': 'mainnet',
            'chainId': 'NetXdQprcVkpaWU',
            'cycle': 1,
            'level': level,
            'hash': f'BL{level}',
            'protocol': 'Proto',
            'nextProtocol': 'Proto',
            'timestamp': '2026-08-02T21:44:52Z',
            'votingEpoch': 1,
            'votingPeriod': 1,
            'knownLevel': level,
            'lastSync': '2026-08-02T21:44:52Z',
            'synced': True,
            'quoteLevel': level,
            'quoteBtc': '0',
            'quoteEur': '0',
            'quoteUsd': '0',
            'quoteCny': '0',
            'quoteJpy': '0',
            'quoteKrw': '0',
            'quoteEth': '0',
            'quoteGbp': '0',
        }
    return frame


@pytest.fixture
async def stand() -> AsyncIterator[tuple[Index[Any, Any, Any], Callable[..., Any]]]:
    original_path = env.PACKAGE_PATH
    env.PACKAGE_PATH = PACKAGE_PATH
    try:
        config = DipDupConfig.load([PACKAGE_PATH / 'dipdup.yaml'])
        config.advanced.rollback_depth = 2
        config.initialize()

        async with AsyncExitStack() as stack:
            dipdup = await create_dummy_dipdup(config, stack)
            index = await spawn_index(dipdup, 'head')
            await index._update_state(status=IndexStatus.realtime, level=1000)

            # NOTE: Wiring the dispatcher does what `DipDup._set_up_datasources` does at runtime
            dispatcher = dipdup._index_dispatcher
            datasource = dipdup._datasources['tzkt']
            assert isinstance(datasource, TezosTzktDatasource)
            datasource.set_sync_level(HeadSubscription(), 1000)
            datasource.call_on_head(dispatcher._on_tzkt_head)
            datasource.call_on_rollback(dispatcher._on_rollback)

            async def feed(action: TezosTzktMessageAction, level: int) -> None:
                await datasource._on_message(
                    TezosTzktMessageType.head,
                    [head_frame(action, level)],
                )

            yield index, feed

            # NOTE: `queues` is a process-wide registry; the next stand spawns the same index
            queues.remove_queue(f'{index.name}:realtime')
    finally:
        env.PACKAGE_PATH = original_path


async def test_reorg_over_queued_level(stand: tuple[Index[Any, Any, Any], Callable[..., Any]]) -> None:
    """Two reorgs arrive while a head message is still queued.

    The first one is for a level the index has received but not applied yet, the second one
    goes deeper. The index drains the queue afterwards, applying the queued level first and
    the rollback second — so the rollback executes from a level below the index's own.
    """
    from reorg.models import Cursor

    index, feed = stand

    # NOTE: Cursor written before the rollback window, e.g. during synchronization
    await Cursor.create(id=1000, level=0, index=0)

    # NOTE: Level 1001 arrives and is applied
    await feed(TezosTzktMessageAction.DATA, 1001)
    await index._process_queue()
    assert index.state.level == 1001

    # NOTE: Level 1002 arrives, but the index is busy elsewhere
    await feed(TezosTzktMessageAction.DATA, 1002)

    # NOTE: Chain reorgs twice in a row while 1002 sits in the queue
    await feed(TezosTzktMessageAction.REORG, 1001)
    await feed(TezosTzktMessageAction.DATA, 1001)
    await feed(TezosTzktMessageAction.REORG, 1000)

    # NOTE: FIFO: level 1002 is applied first, the rollback runs after it
    await index._process_queue()

    assert index.state.level == 1000
    assert await Cursor.filter().count() == 1
    assert (await Cursor.filter().get()).id == 1000
    assert await ModelUpdate.filter(level__gt=1000).count() == 0


async def test_reorg_of_queued_level(stand: tuple[Index[Any, Any, Any], Callable[..., Any]]) -> None:
    """A single reorg arrives for a level the index has received but not applied yet.

    Nothing deeper follows, so this rollback is the only chance to undo that level.
    """
    from reorg.models import Cursor

    index, feed = stand

    await Cursor.create(id=1000, level=0, index=0)

    await feed(TezosTzktMessageAction.DATA, 1001)
    await index._process_queue()

    # NOTE: Level 1002 arrives and is reorged away before the index gets to it
    await feed(TezosTzktMessageAction.DATA, 1002)
    await feed(TezosTzktMessageAction.REORG, 1001)

    await index._process_queue()

    assert index.state.level == 1001
    assert await Cursor.filter().count() == 1
    assert (await Cursor.filter().get()).id == 1001
    assert await ModelUpdate.filter(level__gt=1001).count() == 0


async def test_reorg_with_drained_queue(stand: tuple[Index[Any, Any, Any], Callable[..., Any]]) -> None:
    """Plain reorg with nothing in flight: the index is exactly where the channel thinks it is."""
    from reorg.models import Cursor

    index, feed = stand

    await Cursor.create(id=1000, level=0, index=0)

    for level in (1001, 1002):
        await feed(TezosTzktMessageAction.DATA, level)
        await index._process_queue()
    assert index.state.level == 1002

    await feed(TezosTzktMessageAction.REORG, 1001)
    await index._process_queue()

    assert index.state.level == 1001
    assert await Cursor.filter().count() == 1
    assert (await Cursor.filter().get()).id == 1001
    assert await ModelUpdate.filter(level__gt=1001).count() == 0
