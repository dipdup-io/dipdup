"""A sync drains the realtime queue; messages above the sync level must survive it (#1388)."""

from collections.abc import AsyncIterator
from contextlib import AsyncExitStack
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from dipdup.config import DipDupConfig
from dipdup.index import Index
from dipdup.models import IndexStatus
from dipdup.models import RollbackMessage
from dipdup.test import create_dummy_dipdup
from dipdup.test import spawn_index
from tests import TEST_CONFIGS


def data(level: int) -> tuple[Any, ...]:
    return (SimpleNamespace(level=level),)


@pytest.fixture
async def index(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[Index[Any, Any, Any]]:
    handlers = '[{callback: on_mint, pattern: [{destination: tzbtc_mainnet, entrypoint: mint}]}]'
    index_config = f'{{kind: tezos.operations, datasources: [tzkt], contracts: [tzbtc_mainnet], handlers: {handlers}}}'
    overlay = tmp_path / 'indexes.yaml'
    overlay.write_text(f'indexes:\n  test: {index_config}\n')
    config = DipDupConfig.load([TEST_CONFIGS / 'demo_tezos_token.yaml', overlay], True)

    async with AsyncExitStack() as stack:
        dipdup = await create_dummy_dipdup(config, stack)
        index = await spawn_index(dipdup, 'test')
        await index._update_state(status=IndexStatus.realtime, level=900)
        index.datasources[0].set_sync_level(None, 1000)

        async def synchronize(sync_level: int) -> None:
            await index._update_state(level=sync_level)

        async def rollback(from_level: int, to_level: int) -> None:
            pass

        monkeypatch.setattr(index, '_synchronize', synchronize)
        monkeypatch.setattr(index, '_rollback', rollback)
        yield index


async def test_sync_keeps_messages_above_sync_level(index: Index[Any, Any, Any]) -> None:
    # NOTE: 950 is fetched again by the sync to 1000; 1005 is not, so it must stay queued
    for level in (950, 1005, 1007):
        index.push_realtime_message(data(level))

    assert await index.process()

    assert index.state.level == 1000
    assert [message[0].level for message in index.queue] == [1005, 1007]


async def test_rollback_during_drain_discards_newer_kept_messages(index: Index[Any, Any, Any]) -> None:
    index.push_realtime_message(data(1005))
    index.push_realtime_message(data(1007))
    index.push_realtime_message(RollbackMessage(from_level=1007, to_level=1005))
    index.push_realtime_message(data(1006))

    assert await index.process()

    assert [message[0].level for message in index.queue] == [1005, 1006]
