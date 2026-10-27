"""Watchdog stand: the real `watchdog.run()` loop observes real versioned transactions, hooks and realtime datasources.

Timeouts are 1 second and the loop checks every 0.1 seconds, so every scenario holds the alarm
condition for several consecutive checks.
"""

import asyncio
import itertools
import json
import logging
from collections.abc import AsyncIterator
from collections.abc import Awaitable
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from contextlib import AsyncExitStack
from contextlib import asynccontextmanager
from contextlib import suppress
from dataclasses import dataclass

import pytest
from pysignalr.transport.abstract import ConnectionState
from pysignalr.transport.websocket import WebsocketTransport

from dipdup.config import DipDupConfig
from dipdup.config import HookConfig
from dipdup.config import JobConfig
from dipdup.config import WatchdogAction
from dipdup.config import WatchdogConfig
from dipdup.config import WatchdogTrigger
from dipdup.config.evm_node import EvmNodeDatasourceConfig
from dipdup.context import DipDupContext
from dipdup.context import HookContext
from dipdup.datasources.evm_node import EvmNodeDatasource
from dipdup.datasources.tezos_tzkt import TezosTzktMessageAction
from dipdup.exceptions import WatchdogTimeoutError
from dipdup.scheduler import SchedulerManager
from dipdup.subscriptions.evm_node import EvmNodeHeadSubscription
from dipdup.subscriptions.tezos_tzkt import HeadSubscription
from dipdup.test import create_dummy_dipdup
from dipdup.transactions import TransactionManager
from dipdup.watchdog import watchdog
from tests import tzkt_replay
from tests.test_datasources.test_evm_node import _head_json
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


@pytest.fixture
async def ctx() -> AsyncIterator[DipDupContext]:
    config = DipDupConfig(spec_version='3.0', package='demo_tezos_nft_marketplace')
    async with AsyncExitStack() as stack:
        dipdup = await create_dummy_dipdup(config, stack)
        yield dipdup._ctx


def add_hook(ctx: DipDupContext, name: str, fn: Callable[[HookContext], Awaitable[None]]) -> HookConfig:
    ctx._hooks[name] = HookConfig(callback=name)
    ctx.package._callbacks[f'hooks{name}{name}'] = fn
    return ctx._hooks[name]


def daemon_scheduler(ctx: DipDupContext, fn: Callable[[HookContext], Awaitable[None]]) -> SchedulerManager:
    job = JobConfig(hook=add_hook(ctx, 'daemon', fn), daemon=True)
    job._name = 'daemon'
    return SchedulerManager({'daemon': job})


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


@dataclass
class RealtimeFeed:
    """A realtime datasource driven through its transport: connection state changes and raw frames"""

    name: str
    transport: WebsocketTransport
    send: Callable[[], Awaitable[None]]

    async def connect(self) -> None:
        await self.transport._set_state(ConnectionState.connecting)
        await self.transport._set_state(ConnectionState.connected)

    async def disconnect(self) -> None:
        await self.transport._set_state(ConnectionState.reconnecting)


@asynccontextmanager
async def tzkt_feed() -> AsyncIterator[RealtimeFeed]:
    """TzKT: SignalR invocations on the `head` channel"""
    levels = itertools.count(1001)
    async with tzkt_replay() as tzkt:
        tzkt._subscriptions.add(HeadSubscription())
        tzkt.set_sync_level(HeadSubscription(), 1000)
        transport = tzkt._get_signalr_client()._transport

        async def send() -> None:
            invocation = {
                'type': 1,
                'target': 'head',
                'arguments': [head_frame(TezosTzktMessageAction.DATA, next(levels))],
            }
            await transport._on_raw_message(json.dumps(invocation) + '\x1e')

        yield RealtimeFeed(tzkt.name, transport, send)


@asynccontextmanager
async def node_feed() -> AsyncIterator[RealtimeFeed]:
    """EVM node: JSON-RPC notifications of a `newHeads` subscription"""
    levels = itertools.count(1)
    config = EvmNodeDatasourceConfig(kind='evm.node', url='http://localhost', ws_url='ws://localhost')
    config._name = 'node'
    node = EvmNodeDatasource(config)
    node._subscription_ids['0x1'] = EvmNodeHeadSubscription()
    transport = node._get_ws_client()

    async def send() -> None:
        level = next(levels)
        params = {'subscription': '0x1', 'result': _head_json(f'0x{level:064x}', level)}
        await transport._on_raw_message(json.dumps({'jsonrpc': '2.0', 'method': 'eth_subscription', 'params': params}))

    yield RealtimeFeed(node.name, transport, send)


@pytest.mark.parametrize('feed', [tzkt_feed, node_feed])
async def test_websocket_messages_restart_countdown(
    feed: Callable[[], AbstractAsyncContextManager[RealtimeFeed]],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Every incoming message restarts the countdown; an open connection that falls silent is reported until it closes."""
    config = {WatchdogTrigger.websocket: WatchdogConfig(action=WatchdogAction.warning, timeout=1)}

    async with feed() as datasource, run_watchdog(config):
        await datasource.connect()
        for _ in range(10):
            await datasource.send()
            await asyncio.sleep(0.2)
        flowing = watchdog_messages(caplog, WatchdogTrigger.websocket)
        caplog.clear()

        await asyncio.sleep(1.5)
        silent = watchdog_messages(caplog, WatchdogTrigger.websocket)

        await datasource.disconnect()
        caplog.clear()
        await asyncio.sleep(1.5)
        closed = watchdog_messages(caplog, WatchdogTrigger.websocket)

    assert not flowing, flowing
    assert silent
    assert all(f'datasource `{datasource.name}`' in msg for msg in silent), silent
    assert not closed, closed


@pytest.mark.parametrize('feed', [tzkt_feed, node_feed])
async def test_websocket_silent_from_connect(
    feed: Callable[[], AbstractAsyncContextManager[RealtimeFeed]],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A connection that opens and never delivers a message is reported after the timeout."""
    config = {WatchdogTrigger.websocket: WatchdogConfig(action=WatchdogAction.warning, timeout=1)}

    async with feed() as datasource, run_watchdog(config):
        await datasource.connect()
        await asyncio.sleep(1.5)
        silent = watchdog_messages(caplog, WatchdogTrigger.websocket)
        await datasource.disconnect()

    assert silent
    assert all(f'datasource `{datasource.name}`' in msg for msg in silent), silent


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


async def test_daemon_job_is_not_stuck_callback(ctx: DipDupContext) -> None:
    """A daemon job never returns by design; regular hooks running next to it are still watched."""
    stuck = asyncio.Event()

    async def daemon(ctx: HookContext) -> None:
        await asyncio.Event().wait()

    async def regular(ctx: HookContext) -> None:
        await stuck.wait()

    scheduler = daemon_scheduler(ctx, daemon)
    add_hook(ctx, 'regular', regular)

    config = {WatchdogTrigger.callback: WatchdogConfig(action=WatchdogAction.exception, timeout=1)}
    async with run_watchdog(config) as watchdog_task:
        started = asyncio.Event()
        started.set()
        scheduler_task = asyncio.create_task(scheduler.run(ctx, started))
        try:
            done, _ = await asyncio.wait({watchdog_task, scheduler_task}, timeout=2)
            assert not done

            regular_task = asyncio.create_task(ctx.fire_hook('regular'))
            with pytest.raises(WatchdogTimeoutError, match='hook `regular`'):
                await asyncio.wait_for(asyncio.shield(watchdog_task), timeout=3)
            stuck.set()
            await regular_task
        finally:
            scheduler_task.cancel()
            await scheduler_task


async def daemon_keepalive_hook(ctx: HookContext) -> None:
    ctx.watchdog.heartbeat(WatchdogTrigger.callback)
    await asyncio.Event().wait()


async def test_callback_heartbeat_in_daemon_job(ctx: DipDupContext) -> None:
    """A daemon job is not watched, so a heartbeat inside it has no countdown to restart."""
    scheduler = daemon_scheduler(ctx, daemon_keepalive_hook)

    config = {WatchdogTrigger.callback: WatchdogConfig(action=WatchdogAction.exception, timeout=1)}
    async with run_watchdog(config) as watchdog_task:
        started = asyncio.Event()
        started.set()
        scheduler_task = asyncio.create_task(scheduler.run(ctx, started))
        try:
            done, _ = await asyncio.wait({watchdog_task, scheduler_task}, timeout=2)
            assert not done, [task.exception() for task in done]
        finally:
            scheduler_task.cancel()
            await scheduler_task


async def test_transaction_heartbeat_in_hook_without_transaction(ctx: DipDupContext) -> None:
    """A non-atomic hook runs no transaction, so a transaction heartbeat inside it has no countdown to restart."""

    async def hook(ctx: HookContext) -> None:
        ctx.watchdog.heartbeat(WatchdogTrigger.transaction)

    add_hook(ctx, 'touch', hook)

    config = {WatchdogTrigger.transaction: WatchdogConfig(action=WatchdogAction.exception, timeout=1)}
    async with run_watchdog(config) as watchdog_task:
        await ctx.fire_hook('touch')
        done, _ = await asyncio.wait({watchdog_task}, timeout=1.5)
        assert not done, [task.exception() for task in done]


async def keepalive_hook(ctx: HookContext) -> None:
    for _ in range(12):
        ctx.watchdog.heartbeat(WatchdogTrigger.callback)
        await asyncio.sleep(0.2)


async def keepalive_subtasks_hook(ctx: HookContext) -> None:
    await asyncio.gather(keepalive_hook(ctx), keepalive_hook(ctx))


async def unwatched_hook(ctx: HookContext) -> None:
    ctx.watchdog.reset(WatchdogTrigger.callback)
    await asyncio.sleep(1.5)


@pytest.mark.parametrize('hook', [keepalive_hook, keepalive_subtasks_hook, unwatched_hook])
async def test_callback_heartbeat_without_name(
    ctx: DipDupContext,
    hook: Callable[[HookContext], Awaitable[None]],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """`ctx.watchdog.heartbeat(callback)` keeps the running callback alive, `reset` stops watching it."""
    add_hook(ctx, 'long', hook)

    config = {WatchdogTrigger.callback: WatchdogConfig(action=WatchdogAction.warning, timeout=1)}
    async with run_watchdog(config) as watchdog_task:
        await ctx.fire_hook('long')
        during = watchdog_messages(caplog, WatchdogTrigger.callback)
        caplog.clear()

        # NOTE: The countdown is gone with the callback
        await asyncio.sleep(1.5)
        after = watchdog_messages(caplog, WatchdogTrigger.callback)
        assert not watchdog_task.done()

    assert (len(during), len(after)) == (0, 0), during + after


async def test_callback_heartbeat_after_reset(ctx: DipDupContext, caplog: pytest.LogCaptureFixture) -> None:
    """A heartbeat after `reset` watches the callback again, but not once it has returned."""
    background: list[asyncio.Task[None]] = []

    async def outlive(ctx: HookContext) -> None:
        await asyncio.sleep(0.2)
        ctx.watchdog.heartbeat(WatchdogTrigger.callback)

    async def hook(ctx: HookContext) -> None:
        ctx.watchdog.reset(WatchdogTrigger.callback)
        ctx.watchdog.heartbeat(WatchdogTrigger.callback)
        await asyncio.sleep(1.5)
        background.append(asyncio.create_task(outlive(ctx)))

    add_hook(ctx, 'long', hook)

    config = {WatchdogTrigger.callback: WatchdogConfig(action=WatchdogAction.warning, timeout=1)}
    async with run_watchdog(config):
        await ctx.fire_hook('long')
        during = watchdog_messages(caplog, WatchdogTrigger.callback)
        caplog.clear()

        await background[0]
        await asyncio.sleep(1.5)
        after = watchdog_messages(caplog, WatchdogTrigger.callback)

    assert during
    assert not after, after


async def test_sequential_callbacks_leave_nothing_watched(ctx: DipDupContext) -> None:
    """Callbacks awaited one after another in one task each stop being watched in that task once they return."""
    from dipdup.watchdog import _current

    async def hook(ctx: HookContext) -> None:
        assert len(_current.get()) == (2 if ctx.hook_config.atomic else 1)

    add_hook(ctx, 'plain', hook)
    add_hook(ctx, 'atomic', hook).atomic = True

    config = {
        WatchdogTrigger.callback: WatchdogConfig(action=WatchdogAction.warning, timeout=1),
        WatchdogTrigger.transaction: WatchdogConfig(action=WatchdogAction.warning, timeout=1),
    }
    async with run_watchdog(config):
        for _ in range(3):
            await ctx.fire_hook('plain')
            await ctx.fire_hook('atomic')
            assert _current.get() == ()
