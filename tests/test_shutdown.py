"""Shutdown stand: nothing keeps running after indexing has stopped.

`DipDup.run` spawns background tasks for the index dispatcher, the scheduler, the datasource
loops and monitoring, then waits for them. When one of them fails, the survivors keep their
websockets open until the interpreter goes down, where closing them fails and buries the error
that actually stopped indexing.
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import suppress
from typing import Any

import pytest

from dipdup import env
from dipdup.config import DipDupConfig
from dipdup.dipdup import DipDup
from dipdup.exceptions import FrameworkException
from dipdup.index import Index
from dipdup.performance import queues
from tests import TEST_CONFIGS

PACKAGE_PATH = TEST_CONFIGS.parent / 'packages' / 'reorg'
INDEX_NAME = 'head'


@pytest.fixture
async def config() -> AsyncIterator[DipDupConfig]:
    original_path = env.PACKAGE_PATH
    env.PACKAGE_PATH = PACKAGE_PATH
    try:
        config = DipDupConfig.load([PACKAGE_PATH / 'dipdup.yaml'])
        config.initialize()
        yield config
    finally:
        env.PACKAGE_PATH = original_path
        # NOTE: `queues` is a process-wide registry; the next stand spawns the same index
        with suppress(FrameworkException):
            queues.remove_queue(f'{INDEX_NAME}:realtime')


async def test_failed_index_stops_background_tasks(
    config: DipDupConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failing index leaves no background task behind."""

    async def _failing_process(self: Index[Any, Any, Any]) -> bool:
        raise RuntimeError('callback execution failed')

    async def _skip_initialization(self: DipDup) -> None:
        pass

    # NOTE: Datasources are not initialized to keep the stand offline
    monkeypatch.setattr(DipDup, '_initialize_datasources', _skip_initialization)
    monkeypatch.setattr(Index, 'process', _failing_process)

    with pytest.raises(RuntimeError, match='callback execution failed'):
        await DipDup(config).run()

    leftover = [
        task for task in asyncio.all_tasks() if not task.done() and task.get_name().startswith(('loop:', 'datasource:'))
    ]
    names = sorted(task.get_name() for task in leftover)
    for task in leftover:
        task.cancel()
    await asyncio.gather(*leftover, return_exceptions=True)

    assert names == []
