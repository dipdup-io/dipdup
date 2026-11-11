import asyncio
import socket
from collections.abc import AsyncIterator
from collections.abc import Awaitable
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING
from typing import Any
from unittest.mock import AsyncMock

import pytest
from aiohttp import web

from dipdup.config import HttpConfig
from dipdup.config.evm_node import EvmNodeDatasourceConfig
from dipdup.datasources.evm_node import NODE_LEVEL_TIMEOUT
from dipdup.datasources.evm_node import EvmNodeDatasource
from dipdup.exceptions import DatasourceError
from dipdup.models import MessageType
from dipdup.models.evm_node import EvmNodeHeadData
from dipdup.pysignalr import Message
from dipdup.subscriptions.evm_node import EvmNodeHeadSubscription

if TYPE_CHECKING:
    from dipdup.datasources import IndexDatasource

# NOTE: A project with both an `evm.events` and an `evm.transactions` index on one node datasource
# holds two unequal head subscriptions, so the node opens two identical `newHeads` streams and
# announces every block twice, back to back. See `test_subscriptions.py` for the config side.
PLAIN_HEAD = EvmNodeHeadSubscription()
TRANSACTIONS_HEAD = EvmNodeHeadSubscription(transactions=True)

# NOTE: A healthy emitter loop never returns; it parks on an empty queue. So "drain it" means
# "run it until it stops making progress". Each queued head costs at most one `wait_level` sleep.
DRAIN_TIMEOUT = max(1.0, NODE_LEVEL_TIMEOUT * 20)

BLOCK_HASH = '0x' + 'ab' * 32


def _head_json(block_hash: str, level: int) -> dict[str, Any]:
    return {
        'baseFeePerGas': '0x3b9aca00',
        'difficulty': '0x0',
        'extraData': '0x',
        'gasLimit': '0x1c9c380',
        'gasUsed': '0x5208',
        'hash': block_hash,
        'logsBloom': '0x' + '00' * 256,
        'miner': '0x' + '00' * 20,
        'mixHash': '0x' + '00' * 32,
        'nonce': '0x0000000000000000',
        'number': hex(level),
        'parentHash': '0x' + '11' * 32,
        'receiptsRoot': '0x' + '22' * 32,
        'sha3Uncles': '0x' + '33' * 32,
        'stateRoot': '0x' + '44' * 32,
        'timestamp': hex(1_750_000_000 + level),
        'transactionsRoot': '0x' + '55' * 32,
    }


class Recorder:
    def __init__(self) -> None:
        self.heads: list[int] = []
        self.rollbacks: list[tuple[MessageType, int, int]] = []

    def attach(self, datasource: EvmNodeDatasource) -> None:
        async def on_head(_datasource: EvmNodeDatasource, head: EvmNodeHeadData) -> None:
            self.heads.append(head.level)

        async def on_rollback(
            _datasource: 'IndexDatasource[Any]',
            type_: MessageType,
            from_level: int,
            to_level: int,
        ) -> None:
            self.rollbacks.append((type_, from_level, to_level))

        datasource.call_on_head(on_head)
        datasource.call_on_rollback(on_rollback)


def _node_datasource() -> tuple[EvmNodeDatasource, Recorder]:
    # NOTE: Datasource is never started; the emitter only leaves the process to fetch a full block.
    config = EvmNodeDatasourceConfig(kind='evm.node', url='http://localhost', ws_url='ws://localhost')
    config._name = 'node'

    datasource = EvmNodeDatasource(config)
    datasource.get_block_by_level = AsyncMock(return_value={'transactions': []})  # type: ignore[method-assign]
    recorder = Recorder()
    recorder.attach(datasource)
    return datasource, recorder


async def _drain(datasource: EvmNodeDatasource) -> None:
    try:
        await asyncio.wait_for(datasource._emitter_loop(), timeout=DRAIN_TIMEOUT)
    except TimeoutError:
        pass


async def test_head_is_emitted() -> None:
    datasource, recorder = _node_datasource()

    await datasource._handle_subscription(PLAIN_HEAD, _head_json(BLOCK_HASH, 42))
    await _drain(datasource)

    assert recorder.heads == [42]
    assert recorder.rollbacks == []
    assert dict(datasource._level_data) == {}


async def test_distinct_heads_are_emitted() -> None:
    datasource, recorder = _node_datasource()

    await datasource._handle_subscription(PLAIN_HEAD, _head_json('0x' + 'a1' * 32, 42))
    await datasource._handle_subscription(PLAIN_HEAD, _head_json('0x' + 'a2' * 32, 43))
    await _drain(datasource)

    assert recorder.heads == [42, 43]
    assert recorder.rollbacks == []
    assert dict(datasource._level_data) == {}


async def test_head_from_two_subscriptions_is_emitted_once() -> None:
    datasource, recorder = _node_datasource()

    await datasource._handle_subscription(PLAIN_HEAD, _head_json(BLOCK_HASH, 42))
    await datasource._handle_subscription(TRANSACTIONS_HEAD, _head_json(BLOCK_HASH, 42))
    await _drain(datasource)

    # NOTE: Emitting the second announcement would re-emit the head and, since its level is not
    # greater than the known one, fire a rollback on every EVM channel — a phantom one-level reorg.
    assert recorder.heads == [42]
    assert recorder.rollbacks == []
    assert dict(datasource._level_data) == {}
    # NOTE: Folding the pair must not lose what the second announcement asked for.
    datasource.get_block_by_level.assert_awaited_once_with(block_number=42, full_transactions=True)  # type: ignore[attr-defined]


async def test_head_announced_again_during_emit_is_ignored() -> None:
    datasource, recorder = _node_datasource()

    # NOTE: `on_head` runs inside the emitter pass, after the queue item was taken but before the
    # level data is dropped — the window a queue-membership check would miss.
    async def announce_again(_datasource: EvmNodeDatasource, _head: EvmNodeHeadData) -> None:
        await datasource._handle_subscription(TRANSACTIONS_HEAD, _head_json(BLOCK_HASH, 42))

    datasource.call_on_head(announce_again)

    await datasource._handle_subscription(PLAIN_HEAD, _head_json(BLOCK_HASH, 42))
    await _drain(datasource)

    assert recorder.heads == [42]
    assert recorder.rollbacks == []
    assert dict(datasource._level_data) == {}
    datasource.get_block_by_level.assert_awaited_once_with(block_number=42, full_transactions=True)  # type: ignore[attr-defined]


@asynccontextmanager
async def _node_server(
    on_connect: Callable[[web.WebSocketResponse], Awaitable[None]],
    subscribed: bool = True,
) -> AsyncIterator[tuple[EvmNodeDatasource, list[int]]]:
    """Node datasource on a local websocket server; yields it with a counter of accepted connections"""
    connections: list[int] = []

    async def ws_handler(request: web.Request) -> web.WebSocketResponse:
        connections.append(1)
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await on_connect(ws)
        return ws

    app = web.Application()
    app.router.add_get('/', ws_handler)
    runner = web.AppRunner(app, handle_signals=False, shutdown_timeout=0.1)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 0)
    await site.start()
    host, port = runner.addresses[0]
    try:
        yield _ws_datasource(f'ws://{host}:{port}', subscribed), connections
    finally:
        await runner.cleanup()


def _ws_datasource(ws_url: str, subscribed: bool = True) -> EvmNodeDatasource:
    config = EvmNodeDatasourceConfig(
        kind='evm.node',
        url='http://localhost',
        ws_url=ws_url,
        http=HttpConfig(retry_count=3, retry_sleep=0.01, retry_multiplier=1, connection_timeout=1),
    )
    config._name = 'node'
    datasource = EvmNodeDatasource(config)
    if subscribed:
        datasource._subscriptions.add(PLAIN_HEAD)
    return datasource


async def test_callback_error_is_not_a_connection_error() -> None:
    # NOTE: An error raised while handling a message must stop the datasource as is, not trigger a reconnect
    error = OSError('database is gone')

    async def on_connect(ws: web.WebSocketResponse) -> None:
        await ws.send_json({'jsonrpc': '2.0', 'method': 'eth_subscription', 'params': {}})
        async for _ in ws:
            pass

    async def on_message(message: Message) -> None:
        raise error

    async with _node_server(on_connect) as (datasource, connections), asyncio.timeout(10):
        datasource._on_message = on_message  # type: ignore[method-assign]
        with pytest.raises(OSError) as exc_info:
            await datasource._ws_loop()
    assert exc_info.value is error
    assert len(connections) == 1


@pytest.mark.parametrize('subscribed', [True, False])
async def test_dropped_connection_fails_after_retry_count(subscribed: bool) -> None:
    # NOTE: A connection lost before its subscriptions are confirmed, or without any, is a failed attempt
    async def on_connect(ws: web.WebSocketResponse) -> None:
        await ws.close()

    async with _node_server(on_connect, subscribed) as (datasource, connections), asyncio.timeout(10):
        with pytest.raises(DatasourceError):
            await datasource._ws_loop()
    assert len(connections) == 3


async def test_refused_connection_fails_after_retry_count() -> None:
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        _, port = sock.getsockname()
    datasource = _ws_datasource(f'ws://127.0.0.1:{port}')

    async with asyncio.timeout(10):
        with pytest.raises(DatasourceError) as exc_info:
            await datasource._ws_loop()
    assert isinstance(exc_info.value.__cause__, OSError)
