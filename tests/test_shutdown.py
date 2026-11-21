"""Shutdown stand: nothing keeps running after indexing has stopped.

`DipDup.run` spawns background tasks for the index dispatcher, the scheduler, the datasource
loops and monitoring, then waits for them. When one of them fails, the survivors keep their
websockets open until the interpreter goes down, where closing them fails and a spurious error
is logged next to the one that actually stopped indexing. A task that does not stop when cancelled,
like one waiting for a database that will never answer, must not keep that error from being raised.
"""

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from contextlib import suppress
from typing import Any

import pytest

from dipdup import env
from dipdup.config import DipDupConfig
from dipdup.context import DipDupContext
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

    from dipdup.dipdup import SHUTDOWN_TIMEOUT

    started = time.monotonic()
    with pytest.raises(RuntimeError, match='callback execution failed'):
        await DipDup(config).run()
    # NOTE: Tasks that stop when cancelled must not wait for the shutdown bound
    assert time.monotonic() - started < SHUTDOWN_TIMEOUT / 5

    leftover = [task for task in asyncio.all_tasks() if not task.done() and task.get_name().startswith('loop:')]
    names = sorted(task.get_name() for task in leftover)
    for task in leftover:
        task.cancel()
    await asyncio.gather(*leftover, return_exceptions=True)

    assert names == []


async def test_stuck_task_does_not_block_shutdown(
    config: DipDupConfig,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A task that ignores cancellation does not keep `run` from raising the error that stopped indexing."""
    released = asyncio.Event()

    async def _hooks_loop(self: DipDupContext) -> None:
        # NOTE: Like a query on a dead connection: no cancellation stops it until the pool is terminated
        while not released.is_set():
            with suppress(asyncio.CancelledError):
                await released.wait()

    async def _failing_process(self: Index[Any, Any, Any]) -> bool:
        raise RuntimeError('callback execution failed')

    async def _skip_initialization(self: DipDup) -> None:
        pass

    monkeypatch.setattr(DipDup, '_initialize_datasources', _skip_initialization)
    monkeypatch.setattr(DipDupContext, '_hooks_loop', _hooks_loop)
    monkeypatch.setattr(Index, 'process', _failing_process)
    # NOTE: `raising=False`: before the fix there is no bound to patch, and the run must hang rather than fail here
    monkeypatch.setattr('dipdup.dipdup.SHUTDOWN_TIMEOUT', 0.1, raising=False)

    run = asyncio.create_task(DipDup(config).run())
    try:
        done, _ = await asyncio.wait({run}, timeout=2)
        assert run in done, '`DipDup.run` is still waiting for the cancelled tasks'
        with pytest.raises(RuntimeError, match='callback execution failed'):
            run.result()
        stuck = [task for task in asyncio.all_tasks() if task.get_name() == 'loop:hooks_loop']
        assert stuck and not stuck[0].done()
    finally:
        released.set()
        with suppress(BaseException):
            await run

    warnings = [r.getMessage() for r in caplog.records if r.name == 'dipdup.dipdup' and r.levelno == logging.WARNING]
    assert [message.rsplit(': ', 1)[-1] for message in warnings] == ['loop:hooks_loop'], warnings
