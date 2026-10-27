"""Watchdog stand: the real `watchdog.run()` loop observes real versioned transactions and a TzKT datasource.

Timeouts are 1 second and the loop checks every 0.1 seconds, so every scenario holds the alarm
condition for several consecutive checks.
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack
from contextlib import asynccontextmanager
from contextlib import suppress

import pytest

from dipdup.config import DipDupConfig
from dipdup.config import WatchdogAction
from dipdup.config import WatchdogConfig
from dipdup.config import WatchdogTrigger
from dipdup.datasources.tezos_tzkt import TezosTzktMessageAction
from dipdup.exceptions import WatchdogTimeoutError
from dipdup.subscriptions.tezos_tzkt import HeadSubscription
from dipdup.subscriptions.tezos_tzkt import TezosTzktMessageType
from dipdup.test import create_dummy_dipdup
from dipdup.transactions import TransactionManager
from dipdup.watchdog import watchdog
from tests import tzkt_replay
from tests.test_reorg import head_frame

INTERVAL = 0.1


@asynccontextmanager
async def run_watchdog(config: dict[WatchdogTrigger, WatchdogConfig]) -> AsyncIterator[asyncio.Task[None]]:
    watchdog.initialize(config)
    task = asyncio.create_task(watchdog.run(INTERVAL))
    try:
        yield task
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError, WatchdogTimeoutError):
            await task
        watchdog.initialize({})


@pytest.fixture
async def transactions() -> AsyncIterator[TransactionManager]:
    config = DipDupConfig(spec_version='3.0', package='demo_tezos_nft_marketplace')
    config.advanced.rollback_depth = 2
    async with AsyncExitStack() as stack:
        dipdup = await create_dummy_dipdup(config, stack)
        yield dipdup._transactions


async def fetch_metadata(reply: asyncio.Event) -> None:
    await reply.wait()


async def stuck_level(transactions: TransactionManager, index: str, reply: asyncio.Event) -> None:
    async with transactions.in_transaction(level=1001, sync_level=1001, index=index):
        await fetch_metadata(reply)


def watchdog_messages(caplog: pytest.LogCaptureFixture, trigger: WatchdogTrigger) -> list[str]:
    return [
        record.getMessage()
        for record in caplog.records
        if record.name == 'dipdup.watchdog'
        and record.levelno >= logging.WARNING
        and f'`{trigger.value}`' in record.getMessage()
    ]


async def test_transaction_stuck_while_others_commit(transactions: TransactionManager) -> None:
    """A transaction queued behind another one gets stuck after the first one has committed."""
    config = {WatchdogTrigger.transaction: WatchdogConfig(action=WatchdogAction.exception, timeout=1)}
    reply, other_done = asyncio.Event(), asyncio.Event()

    async def other_level() -> None:
        async with transactions.in_transaction(level=1001, sync_level=1001, index='head_00'):
            await other_done.wait()

    async with run_watchdog(config) as watchdog_task:
        other = asyncio.create_task(other_level())
        await asyncio.sleep(INTERVAL)
        stuck = asyncio.create_task(stuck_level(transactions, 'head_07', reply))
        await asyncio.sleep(INTERVAL)
        other_done.set()
        await other

        try:
            with pytest.raises(WatchdogTimeoutError, match='head_07'):
                await asyncio.wait_for(asyncio.shield(watchdog_task), timeout=3)
        finally:
            reply.set()
            await stuck


async def test_transaction_timeout_names_index_and_level(
    transactions: TransactionManager,
    caplog: pytest.LogCaptureFixture,
) -> None:
    config = {WatchdogTrigger.transaction: WatchdogConfig(action=WatchdogAction.warning, timeout=1)}
    reply = asyncio.Event()

    async with run_watchdog(config):
        stuck = asyncio.create_task(stuck_level(transactions, 'head_07', reply))
        await asyncio.sleep(1.5)
        reply.set()
        await stuck

    messages = watchdog_messages(caplog, WatchdogTrigger.transaction)
    assert messages
    assert all('head_07' in msg and '1001' in msg for msg in messages), messages


async def test_transaction_timeout_shows_stack_once(
    transactions: TransactionManager,
    caplog: pytest.LogCaptureFixture,
) -> None:
    config = {WatchdogTrigger.transaction: WatchdogConfig(action=WatchdogAction.warning, timeout=1)}
    reply = asyncio.Event()

    async with run_watchdog(config):
        stuck = asyncio.create_task(stuck_level(transactions, 'head_07', reply))
        await asyncio.sleep(1.6)
        reply.set()
        await stuck

    messages = watchdog_messages(caplog, WatchdogTrigger.transaction)
    assert len(messages) > 2
    stacks = [msg for msg in messages if 'in fetch_metadata' in msg]
    assert len(stacks) == 1, messages
    assert 'in stuck_level' in stacks[0]


async def test_websocket_silent_after_data(caplog: pytest.LogCaptureFixture) -> None:
    """The connection stays up, but the head channel stops delivering blocks."""
    config = {WatchdogTrigger.websocket: WatchdogConfig(action=WatchdogAction.warning, timeout=1)}

    async with tzkt_replay() as tzkt, run_watchdog(config):
        tzkt._subscriptions.add(HeadSubscription())
        tzkt.set_sync_level(HeadSubscription(), 1000)
        await tzkt._on_connected()
        await tzkt._on_message(TezosTzktMessageType.head, [head_frame(TezosTzktMessageAction.DATA, 1001)])
        await asyncio.sleep(1.5)

        messages = watchdog_messages(caplog, WatchdogTrigger.websocket)
        assert messages
        assert all('tzkt' in msg for msg in messages), messages

        await tzkt._on_disconnected()
        caplog.clear()
        await asyncio.sleep(1.5)
        assert not watchdog_messages(caplog, WatchdogTrigger.websocket)


async def test_heartbeat_without_name(caplog: pytest.LogCaptureFixture) -> None:
    """`ctx.watchdog.heartbeat(trigger)` keeps a single countdown for the trigger."""
    config = {WatchdogTrigger.websocket: WatchdogConfig(action=WatchdogAction.warning, timeout=1)}

    async with run_watchdog(config):
        watchdog.heartbeat(WatchdogTrigger.websocket)
        await asyncio.sleep(1.3)
        assert watchdog_messages(caplog, WatchdogTrigger.websocket)

        watchdog.reset(WatchdogTrigger.websocket)
        caplog.clear()
        await asyncio.sleep(0.3)
        assert not watchdog_messages(caplog, WatchdogTrigger.websocket)
