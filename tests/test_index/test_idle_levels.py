"""Realtime levels an index reaches without matching anything are saved by the dispatcher in one batch."""

from collections import deque
from collections.abc import AsyncIterator
from collections.abc import Iterator
from contextlib import AsyncExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from dipdup import models
from dipdup.config import DipDupConfig
from dipdup.dipdup import DipDup
from dipdup.index import Index
from dipdup.models import IndexStatus
from dipdup.models import RollbackMessage
from dipdup.performance import queues
from dipdup.subscriptions.tezos_tzkt import TezosTzktMessageType
from dipdup.test import create_dummy_dipdup
from dipdup.test import spawn_index
from tests import TEST_CONFIGS

NAMES = ('first', 'second')


@dataclass(frozen=True)
class Item:
    level: int


async def saved_level(name: str) -> int:
    return (await models.Index.get(name=name)).level


async def idle(index: Index[Any, Any, Any], *levels: int) -> None:
    """Process realtime messages of levels that match nothing"""
    for level in levels:
        index.push_realtime_message((Item(level),))
    await index._process_queue()


@pytest.fixture
async def dipdup(tmp_path: Path) -> AsyncIterator[DipDup]:
    # NOTE: Two copies of the tzBTC index without level bounds
    handlers = '[{callback: on_mint, pattern: [{destination: tzbtc_mainnet, entrypoint: mint}]}]'
    index_config = f'{{kind: tezos.operations, datasources: [tzkt], contracts: [tzbtc_mainnet], handlers: {handlers}}}'
    overlay = tmp_path / 'indexes.yaml'
    overlay.write_text('indexes:\n' + ''.join(f'  {name}: {index_config}\n' for name in NAMES))
    config = DipDupConfig.load([TEST_CONFIGS / 'demo_tezos_token.yaml', overlay], True)
    config.advanced.rollback_depth = 10

    async with AsyncExitStack() as stack:
        dipdup = await create_dummy_dipdup(config, stack)
        for name in NAMES:
            index = await spawn_index(dipdup, name)
            await index._update_state(status=IndexStatus.realtime, level=1000)
            index.datasources[0].set_sync_level(None, 1000)
            # NOTE: Every level is idle unless a test fires a handler itself
            index._match_level_data = lambda handlers, level_data: deque()  # type: ignore[method-assign]
        yield dipdup


def get_index(dipdup: DipDup, name: str = NAMES[0]) -> Index[Any, Any, Any]:
    return dipdup._index_dispatcher._indexes[name]


async def test_idle_levels_saved_in_one_statement(dipdup: DipDup, monkeypatch: pytest.MonkeyPatch) -> None:
    saves: list[str] = []
    batches: list[list[str]] = []
    original_save, original_bulk_update = models.Index.save, models.Index.bulk_update

    async def save(self: models.Index, *args: Any, **kwargs: Any) -> None:
        saves.append(self.name)
        await original_save(self, *args, **kwargs)

    def bulk_update(objects: list[models.Index], *args: Any, **kwargs: Any) -> Any:
        batches.append([o.name for o in objects])
        return original_bulk_update(objects, *args, **kwargs)

    monkeypatch.setattr(models.Index, 'save', save)
    monkeypatch.setattr(models.Index, 'bulk_update', bulk_update)

    for name in NAMES:
        await idle(get_index(dipdup, name), 1001, 1002, 1003)

    assert saves == []
    for name in NAMES:
        assert get_index(dipdup, name).state.level == 1003
        assert await saved_level(name) == 1000

    await dipdup._index_dispatcher._save_idle_levels()

    assert batches == [list(NAMES)]
    for name in NAMES:
        assert await saved_level(name) == 1003

    # NOTE: Nothing new, nothing to write
    await dipdup._index_dispatcher._save_idle_levels()
    assert len(batches) == 1


async def test_restart_refetches_idle_levels(dipdup: DipDup, monkeypatch: pytest.MonkeyPatch) -> None:
    index = get_index(dipdup)
    await idle(index, 1001)

    # NOTE: A matched level saves the level in the handler transaction, with the data
    async with dipdup._ctx.transactions.in_transaction(level=1002, index=index.name):
        await index._update_state(level=1002)
    await idle(index, 1003, 1004)
    assert index.state.level == 1004

    # NOTE: Crash before the dispatcher saved anything: the next process starts from the database
    state = await models.Index.get(name=index.name)
    assert state.level == 1002
    queues.remove_queue(f'{index.name}:realtime')
    restarted = await dipdup._ctx._spawn_index(index.name, state=state)
    restarted.datasources[0].set_sync_level(None, 1004)

    synced: list[tuple[int, int]] = []

    async def synchronize(sync_level: int) -> None:
        synced.append((restarted.state.level, sync_level))

    monkeypatch.setattr(restarted, '_synchronize', synchronize)
    assert await restarted.process()

    # NOTE: Refetches exactly the idle levels 1003-1004; the matched 1002 is not applied twice
    assert synced == [(1002, 1004)]


async def test_rollback_checks_in_memory_level(dipdup: DipDup) -> None:
    index = get_index(dipdup)
    await idle(index, 1001, 1002, 1003)
    assert await saved_level(index.name) == 1000

    # NOTE: The database level (1000) is below `to_level`; the dispatcher must still pass the message on
    await dipdup._index_dispatcher._on_rollback(
        index.datasources[0],
        TezosTzktMessageType.operation,
        from_level=1003,
        to_level=1001,
    )
    assert index.queue == deque([RollbackMessage(1003, 1001)])
    assert index.state.level == 1003

    # NOTE: ...and the index must not take it for an outdated one
    await index._process_queue()
    assert index.state.level == 1001
    assert await saved_level(index.name) == 1001

    # NOTE: Levels after the rollback are saved by the dispatcher, not reloaded from the database
    await idle(index, 1002)
    assert await index.process() is False
    assert index.state.level == 1002
    await dipdup._index_dispatcher._save_idle_levels()
    assert await saved_level(index.name) == 1002


async def test_save_keeps_rolled_back_level(dipdup: DipDup) -> None:
    index = get_index(dipdup)
    await idle(index, 1001, 1002, 1003, 1004)
    assert index.state.level == 1004
    assert await saved_level(index.name) == 1000

    # NOTE: `ctx.rollback` called outside `on_index_rollback`; the index reloads the level on its next `process`
    await dipdup._ctx.rollback(index=index.name, from_level=1004, to_level=1001)
    await dipdup._index_dispatcher._save_idle_levels()
    assert await saved_level(index.name) == 1001

    await index.process()
    assert index.state.level == 1001


async def test_sync_saves_idle_levels(dipdup: DipDup, monkeypatch: pytest.MonkeyPatch) -> None:
    """`_synchronize` doesn't return to the dispatcher until it's done, so it can't leave levels to it."""
    import dipdup.indexes.tezos_operations.index as operations_index

    index = get_index(dipdup)
    index.datasources[0].set_sync_level(None, 1500)

    class CrashingFetcher:
        async def fetch_by_level(self) -> AsyncIterator[tuple[int, tuple[Item]]]:
            for level in range(1001, 1301):
                yield level, (Item(level),)
            raise RuntimeError('crash in the middle of sync')

    async def create_fetcher(first_level: int, sync_level: int) -> CrashingFetcher:
        assert (first_level, sync_level) == (1001, 1500)
        return CrashingFetcher()

    def extract_operation_subgroups(operations: tuple[Item], **kwargs: Any) -> Iterator[Item]:
        return iter(operations)

    monkeypatch.setattr(index, '_create_fetcher', create_fetcher)
    monkeypatch.setattr(operations_index, 'extract_operation_subgroups', extract_operation_subgroups)

    with pytest.raises(RuntimeError, match='crash in the middle of sync'):
        await index.process()

    # NOTE: A restart resumes after the last synced level instead of fetching the whole range again
    assert index.state.status == IndexStatus.syncing
    assert await saved_level(index.name) == 1300
