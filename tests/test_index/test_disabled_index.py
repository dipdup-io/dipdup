"""An index that reached its `last_level` stays in the dispatcher as disabled and must not affect the others."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack
from contextlib import suppress
from pathlib import Path

import pytest

from dipdup.config import DipDupConfig
from dipdup.dipdup import DipDup
from dipdup.models import IndexStatus
from dipdup.test import create_dummy_dipdup
from dipdup.test import spawn_index
from tests import TEST_CONFIGS

NAMES = ('running', 'finished')


@pytest.fixture
async def dipdup(tmp_path: Path) -> AsyncIterator[DipDup]:
    # NOTE: Two copies of the tzBTC index; `finished` has reached its last level
    handlers = '[{callback: on_mint, pattern: [{destination: tzbtc_mainnet, entrypoint: mint}]}]'
    index_config = f'{{kind: tezos.operations, datasources: [tzkt], contracts: [tzbtc_mainnet], handlers: {handlers}}}'
    overlay = tmp_path / 'indexes.yaml'
    overlay.write_text('indexes:\n' + ''.join(f'  {name}: {index_config}\n' for name in NAMES))
    config = DipDupConfig.load([TEST_CONFIGS / 'demo_tezos_token.yaml', overlay], True)

    async with AsyncExitStack() as stack:
        dipdup = await create_dummy_dipdup(config, stack)
        for name, status in zip(NAMES, (IndexStatus.realtime, IndexStatus.disabled), strict=True):
            index = await spawn_index(dipdup, name)
            await index._update_state(status=status, level=1000)
            index.datasources[0].set_sync_level(None, 1000)
        yield dipdup


async def test_disabled_index_does_not_hold_back_realtime(dipdup: DipDup, monkeypatch: pytest.MonkeyPatch) -> None:
    dispatcher = dipdup._index_dispatcher
    synchronized = 0

    async def noop() -> None:
        pass

    async def on_synchronized() -> None:
        nonlocal synchronized
        synchronized += 1

    for datasource in dipdup._ctx.datasources.values():
        monkeypatch.setattr(datasource, 'subscribe', noop)
    # NOTE: The fixture has spawned the indexes already
    monkeypatch.setattr(dispatcher, '_load_index_state', noop)
    monkeypatch.setattr(dispatcher, '_subscribe_to_datasource_events', noop)
    monkeypatch.setattr(dispatcher, '_on_synchronized', on_synchronized)
    start_scheduler, start_datasources = asyncio.Event(), asyncio.Event()

    with suppress(TimeoutError):
        await asyncio.wait_for(dispatcher.run(start_datasources, start_scheduler, early_realtime=False), 0.5)

    assert start_datasources.is_set()
    assert synchronized == 1
    assert start_scheduler.is_set()


async def test_disabled_index_gets_no_realtime_messages(dipdup: DipDup) -> None:
    dispatcher = dipdup._index_dispatcher
    running, finished = (dispatcher._indexes[name] for name in NAMES)

    for index in (running, finished):
        index.push_realtime_message(())

    assert len(running.queue) == 1
    assert len(finished.queue) == 0


async def test_messages_collected_during_sync_are_dropped_on_disable(dipdup: DipDup) -> None:
    index = dipdup._index_dispatcher._indexes['running']
    await index._update_state(status=IndexStatus.syncing, level=900)
    index.push_realtime_message(())
    assert len(index.queue) == 1

    await index._enter_disabled_state(1000)

    assert len(index.queue) == 0


async def test_failed_index_keeps_its_realtime_messages(dipdup: DipDup) -> None:
    # NOTE: Only disabled indexes are skipped by the dispatcher; any other status is still processed
    index = dipdup._index_dispatcher._indexes['running']
    await index._update_state(status=IndexStatus.failed, level=1000)

    index.push_realtime_message(())

    assert len(index.queue) == 1
