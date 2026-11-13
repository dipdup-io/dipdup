import time
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

import dipdup.dipdup as dipdup_module
from dipdup.dipdup import IndexDispatcher
from dipdup.exceptions import FrameworkException
from dipdup.models import Meta
from dipdup.performance import metrics

_STATUS_METRICS = ('levels_indexed', 'levels_total', 'progress', 'realtime_at', 'synchronized_at', 'time_left')


class FakeIndex:
    def __init__(self, level: int, sync_level: int | None, first_level: int = 0, last_level: int = 0) -> None:
        self.name = f'index_{id(self)}'
        self.sync_level = sync_level
        self.state = SimpleNamespace(level=level)
        self._config = SimpleNamespace(first_level=first_level, last_level=last_level)
        self.is_active = self.is_synchronized = self.is_realtime = False

    def get_sync_level(self) -> int:
        if self.sync_level is None:
            raise FrameworkException('Neither current nor sync level is known')
        return self.sync_level


@pytest.fixture
def dispatcher() -> Iterator[IndexDispatcher]:
    saved = {name: getattr(metrics, name) for name in _STATUS_METRICS}
    for name in _STATUS_METRICS:
        setattr(metrics, name, 0)
    dispatcher = IndexDispatcher(MagicMock())
    dispatcher._started_at = time.time() - 10
    with (
        patch.object(dipdup_module, 'fire_and_forget', MagicMock()),
        patch.object(Meta, 'update_or_create', MagicMock()),
    ):
        yield dispatcher
    for name, value in saved.items():
        setattr(metrics, name, value)


async def _tick(dispatcher: IndexDispatcher, *indexes: FakeIndex) -> tuple[float, int, str]:
    dispatcher._indexes = {index.name: index for index in indexes}  # type: ignore[misc]
    await dispatcher._update_metrics()
    left = int(metrics.levels_total) - int(metrics.levels_indexed)
    return round(float(metrics.progress) * 100, 1), left, dispatcher._get_status()


async def test_progress_survives_restart(dispatcher: IndexDispatcher) -> None:
    index = FakeIndex(level=900_000, sync_level=1_000_000)

    assert (await _tick(dispatcher, index))[:2] == (90.0, 100_000)

    index.state.level = 950_000
    progress, left, status = await _tick(dispatcher, index)
    assert (progress, left) == (95.0, 50_000)
    assert ' 95.0% done, 50000 levels left' in status


async def test_progress_counts_from_first_level(dispatcher: IndexDispatcher) -> None:
    index = FakeIndex(level=750_000, sync_level=1_000_000, first_level=500_000)

    assert (await _tick(dispatcher, index))[:2] == (50.0, 250_000)


async def test_progress_stops_at_last_level(dispatcher: IndexDispatcher) -> None:
    index = FakeIndex(level=200_000, sync_level=1_000_000, last_level=200_000)

    assert (await _tick(dispatcher, index))[:2] == (100.0, 0)


async def test_index_without_level_counts_as_not_started(dispatcher: IndexDispatcher) -> None:
    syncing, fresh = FakeIndex(level=100_000, sync_level=1_000_000), FakeIndex(level=0, sync_level=1_000_000)

    assert (await _tick(dispatcher, syncing, fresh))[:2] == (5.0, 1_900_000)

    syncing.state.level = 600_000
    assert (await _tick(dispatcher, syncing, fresh))[:2] == (30.0, 1_400_000)


async def test_index_that_skips_history(dispatcher: IndexDispatcher) -> None:
    index = FakeIndex(level=0, sync_level=1_000_000)

    progress, _, status = await _tick(dispatcher, index)
    assert progress == 0.0
    assert 'done' not in status

    index.state.level = 1_000_000
    progress, left, status = await _tick(dispatcher, index)
    assert (progress, left) == (100.0, 0)
    assert '100.0% done, 0 levels left' in status


async def test_one_lagging_index_among_synced(dispatcher: IndexDispatcher) -> None:
    synced = [FakeIndex(level=1_000_000, sync_level=1_000_000) for _ in range(441)]
    lagging = FakeIndex(level=50_000, sync_level=1_000_000)

    assert (await _tick(dispatcher, *synced, lagging))[:2] == (99.8, 950_000)


async def test_growing_sync_level(dispatcher: IndexDispatcher) -> None:
    index = FakeIndex(level=550_000, sync_level=1_000_000)

    assert (await _tick(dispatcher, index))[:2] == (55.0, 450_000)

    index.sync_level = 1_100_000
    assert (await _tick(dispatcher, index))[:2] == (50.0, 550_000)


async def test_rollback_does_not_go_below_zero(dispatcher: IndexDispatcher) -> None:
    index = FakeIndex(level=1_000_010, sync_level=1_000_100, first_level=1_000_000)

    assert (await _tick(dispatcher, index))[:2] == (10.0, 90)

    index.state.level = 999_995
    assert (await _tick(dispatcher, index))[:2] == (0.0, 100)


async def test_first_level_above_head(dispatcher: IndexDispatcher) -> None:
    index = FakeIndex(level=0, sync_level=1_000_000, first_level=2_000_000)

    assert (await _tick(dispatcher, index))[:2] == (100.0, 0)


async def test_unknown_sync_level_keeps_previous_values(dispatcher: IndexDispatcher) -> None:
    index = FakeIndex(level=500_000, sync_level=1_000_000)
    assert (await _tick(dispatcher, index))[:2] == (50.0, 500_000)

    index.state.level, index.sync_level = 600_000, None
    assert (await _tick(dispatcher, index))[:2] == (50.0, 500_000)


async def test_time_left_uses_speed_of_this_run(dispatcher: IndexDispatcher) -> None:
    index = FakeIndex(level=900_000, sync_level=1_000_000)
    await _tick(dispatcher, index)
    assert float(metrics.time_left) == 0.0

    index.state.level = 950_000
    await _tick(dispatcher, index)
    # NOTE: 50k levels in about 10 seconds of this run, 50k more to go
    assert 9 < float(metrics.time_left) < 11


async def test_realtime_status_counts_levels_of_this_run(dispatcher: IndexDispatcher) -> None:
    index: Any = FakeIndex(level=1_000_000, sync_level=1_000_000)
    await _tick(dispatcher, index)

    index.state.level = index.sync_level = 1_000_100
    metrics.realtime_at = time.time()
    assert (await _tick(dispatcher, index))[2] == 'realtime: 100 levels indexed and counting'


async def test_status_is_not_rounded_up_to_100(dispatcher: IndexDispatcher) -> None:
    index = FakeIndex(level=15_799_000, sync_level=15_799_875)

    assert ' 99.9% done, 875 levels left' in (await _tick(dispatcher, index))[2]
