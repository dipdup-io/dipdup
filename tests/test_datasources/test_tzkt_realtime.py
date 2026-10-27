import asyncio
import socket
import time
import uuid
from collections.abc import AsyncIterator
from collections.abc import Awaitable
from collections.abc import Callable
from collections.abc import Coroutine
from contextlib import asynccontextmanager
from contextlib import suppress
from typing import Any

import orjson as json
import pytest
from aiohttp import WSMsgType
from aiohttp import web

from dipdup.config import HttpConfig
from dipdup.config.tezos_tzkt import TezosTzktDatasourceConfig
from dipdup.datasources.tezos_tzkt import TezosTzktDatasource
from dipdup.exceptions import DatasourceError
from dipdup.subscriptions.tezos_tzkt import HeadSubscription
from dipdup.subscriptions.tezos_tzkt import TezosTzktMessageType
from dipdup.subscriptions.tezos_tzkt import TransactionSubscription

RS = '\x1e'
LEVEL = 100
CLOSE_ERROR = "Connection closed with an error. OperationCanceledException: Client hasn't sent a message/ping within the configured ClientTimeoutInterval."


class Connection:
    def __init__(self, request: web.Request, ws: web.WebSocketResponse) -> None:
        self.request = request
        self.ws = ws
        self.invocations: list[dict[str, Any]] = []

    async def send(self, message: dict[str, Any]) -> None:
        await self.ws.send_str(json.dumps(message).decode() + RS)

    async def complete(self, invocation_id: str, result: Any = None, error: str | None = None) -> None:
        message: dict[str, Any] = {'type': 3, 'invocationId': invocation_id}
        if error is None:
            message['result'] = result
        else:
            message['error'] = error
        await self.send(message)

    async def push(self, target: str, level: int, data: Any) -> None:
        await self.send({'type': 1, 'target': target, 'arguments': [{'type': 1, 'state': level, 'data': data}]})

    def abort(self) -> None:
        # NOTE: TCP-level drop without a close frame
        if self.request.transport:
            self.request.transport.abort()


class FakeTzkt:
    """TzKT REST and SignalR endpoints. Like ASP.NET Core, a connection id is good for a single websocket."""

    def __init__(self) -> None:
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            self.port = sock.getsockname()[1]
        self.url = f'http://127.0.0.1:{self.port}'
        self.connections: list[Connection] = []
        self.negotiations = 0
        self.negotiate_hook: Callable[[web.Request], Awaitable[web.StreamResponse | None]] | None = None
        self.invocation_hook: Callable[[Connection, dict[str, Any]], Coroutine[Any, Any, None]] = self.confirm
        self._connection_ids: set[str] = set()
        self._tasks: set[asyncio.Task[None]] = set()
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None

    async def confirm(self, connection: Connection, invocation: dict[str, Any]) -> None:
        await connection.complete(invocation['invocationId'], result=LEVEL)

    async def _protocol(self, request: web.Request) -> web.Response:
        return web.json_response({'code': 1, 'hash': 'P' * 51})

    async def _negotiate(self, request: web.Request) -> web.StreamResponse:
        self.negotiations += 1
        if self.negotiate_hook and (response := await self.negotiate_hook(request)):
            return response
        connection_id = uuid.uuid4().hex
        self._connection_ids.add(connection_id)
        return web.json_response(
            {
                'negotiateVersion': 0,
                'connectionId': connection_id,
                'availableTransports': [{'transport': 'WebSockets', 'transferFormats': ['Text']}],
            }
        )

    async def _ws(self, request: web.Request) -> web.StreamResponse:
        connection_id = request.query.get('id', '')
        if connection_id not in self._connection_ids:
            return web.Response(status=404)
        self._connection_ids.remove(connection_id)

        ws = web.WebSocketResponse()
        await ws.prepare(request)
        connection = Connection(request, ws)
        async for raw in ws:
            if raw.type != WSMsgType.TEXT:
                break
            for part in filter(None, raw.data.split(RS)):
                message = json.loads(part)
                if 'protocol' in message:
                    await ws.send_str('{}' + RS)
                    self.connections.append(connection)
                elif message.get('type') == 1:
                    connection.invocations.append(message)
                    task = asyncio.create_task(self.invocation_hook(connection, message))
                    self._tasks.add(task)
                    task.add_done_callback(self._tasks.discard)
        return ws

    async def start(self) -> None:
        app = web.Application()
        app.router.add_get('/v1/protocols/current', self._protocol)
        app.router.add_post('/v1/ws/negotiate', self._negotiate)
        app.router.add_get('/v1/ws', self._ws)
        self._runner = web.AppRunner(app, handle_signals=False, shutdown_timeout=0.1)
        await self._runner.setup()
        await self.listen()

    async def listen(self) -> None:
        assert self._runner
        self._site = web.TCPSite(self._runner, '127.0.0.1', self.port, reuse_address=True)
        await self._site.start()

    async def go_down(self) -> None:
        assert self._site
        await self._site.stop()
        for connection in self.connections:
            connection.abort()

    async def stop(self) -> None:
        for connection in self.connections:
            connection.abort()
        if self._runner:
            await self._runner.cleanup()


async def wait_until(predicate: Callable[[], bool], timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        await asyncio.sleep(0.01)
    return predicate()


@asynccontextmanager
async def fake_tzkt() -> AsyncIterator[tuple[FakeTzkt, TezosTzktDatasource]]:
    server = FakeTzkt()
    await server.start()
    config = TezosTzktDatasourceConfig(
        kind='tezos.tzkt',
        url=server.url,
        http=HttpConfig(
            retry_count=30,
            retry_sleep=0.01,
            retry_multiplier=1,
            connection_timeout=1,
            request_timeout=1,
        ),
    )
    config._name = 'tzkt'
    tzkt = TezosTzktDatasource(config)
    try:
        async with tzkt:
            yield server, tzkt
    finally:
        await server.stop()


@asynccontextmanager
async def realtime(tzkt: TezosTzktDatasource) -> AsyncIterator[asyncio.Task[None]]:
    task = asyncio.create_task(tzkt.run())
    try:
        yield task
    finally:
        task.cancel()
        with suppress(BaseException):
            await task


async def subscribe(tzkt: TezosTzktDatasource, timeout: float = 5) -> None:
    try:
        await asyncio.wait_for(tzkt.subscribe(), timeout)
    except TimeoutError:
        pytest.fail(f'`subscribe` blocked for {timeout}s')


async def resubscribe(tzkt: TezosTzktDatasource, timeout: float = 5) -> None:
    """Call `subscribe` like `IndexDispatcher` does: on every iteration while subscriptions are missing."""
    deadline = time.monotonic() + timeout
    while tzkt._subscriptions.missing_subscriptions:
        assert time.monotonic() < deadline, 'Subscriptions were not restored'
        await subscribe(tzkt, timeout)
        await asyncio.sleep(0.01)


async def test_realtime_survives_repeated_drops() -> None:
    async with fake_tzkt() as (server, tzkt):
        tzkt._subscriptions.add(HeadSubscription())
        async with realtime(tzkt) as task:
            await resubscribe(tzkt)

            async def drop() -> None:
                connections = len(server.connections)
                server.connections[-1].abort()
                await wait_until(lambda: len(server.connections) > connections or task.done(), 5)

            for number in range(1, 12):
                await drop()
                assert not task.done(), f'Realtime loop died after drop #{number}: {task.exception()!r}'
                assert len(server.connections) == number + 1


async def test_realtime_survives_long_negotiation_outage() -> None:
    async with fake_tzkt() as (server, tzkt):
        failed = 0

        async def negotiate_hook(request: web.Request) -> web.StreamResponse | None:
            nonlocal failed
            if server.connections and failed < 11:
                failed += 1
                # NOTE: Proxy resets the connection; client sees `ServerDisconnectedError`
                if request.transport:
                    request.transport.abort()
                return web.Response()
            return None

        tzkt._subscriptions.add(HeadSubscription())
        async with realtime(tzkt) as task:
            await resubscribe(tzkt)
            server.negotiate_hook = negotiate_hook
            server.connections[-1].abort()

            await wait_until(lambda: len(server.connections) > 1 or task.done(), 30)
            assert not task.done(), f'Realtime loop died: {task.exception()!r}'
            assert failed == 11
            assert len(server.connections) == 2


async def test_realtime_survives_connection_refused() -> None:
    async with fake_tzkt() as (server, tzkt):
        await server.go_down()
        async with realtime(tzkt) as task:
            await asyncio.sleep(0.1)
            await server.listen()

            await wait_until(lambda: bool(server.connections) or task.done(), 5)
            assert not task.done(), f'Realtime loop died: {task.exception()!r}'
            assert server.connections


async def test_rejected_subscription_fails_subscribe() -> None:
    async with fake_tzkt() as (server, tzkt):

        async def invocation_hook(connection: Connection, invocation: dict[str, Any]) -> None:
            if invocation['target'] == 'SubscribeToOperations':
                error = "An unexpected error occurred invoking 'SubscribeToOperations' on the server. HubException: Subscriptions limit exceeded"
                await connection.complete(invocation['invocationId'], error=error)
            else:
                await server.confirm(connection, invocation)

        server.invocation_hook = invocation_hook
        tzkt.set_sync_level(None, LEVEL)
        tzkt._subscriptions.add(HeadSubscription())
        tzkt._subscriptions.add(TransactionSubscription(address='KT1PDrBE59Zmxnb8vXRgRAG1XmvTMTs5EDHU'))
        async with realtime(tzkt) as task:
            assert await wait_until(lambda: bool(server.connections), 5)

            with pytest.raises(DatasourceError, match='Subscriptions limit exceeded'):
                await subscribe(tzkt)
            assert not task.done(), f'Realtime loop died: {task.exception()!r}'

            # NOTE: The connection is still alive and delivers messages
            await server.connections[-1].push('head', LEVEL + 1, {})
            assert await wait_until(lambda: tzkt.get_channel_level(TezosTzktMessageType.head) == LEVEL + 1, 5)


async def test_late_completion_after_cancelled_subscribe() -> None:
    async with fake_tzkt() as (server, tzkt):

        async def invocation_hook(connection: Connection, invocation: dict[str, Any]) -> None:
            await asyncio.sleep(0.2)
            await server.confirm(connection, invocation)

        server.invocation_hook = invocation_hook
        tzkt.set_sync_level(None, LEVEL)
        tzkt._subscriptions.add(HeadSubscription())
        async with realtime(tzkt) as task:
            assert await wait_until(lambda: bool(server.connections), 5)

            # NOTE: The caller gives up on `subscribe`; the completion arrives afterwards
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(tzkt.subscribe(), 0.05)
            await asyncio.sleep(0.3)
            assert not task.done(), f'Realtime loop died: {task.exception()!r}'

            await server.connections[-1].push('head', LEVEL + 1, {})
            assert await wait_until(lambda: tzkt.get_channel_level(TezosTzktMessageType.head) == LEVEL + 1, 5)


@pytest.mark.parametrize('close', ['abort', 'error'])
async def test_subscribe_released_when_connection_lost(close: str) -> None:
    async with fake_tzkt() as (server, tzkt):
        lost = False

        async def invocation_hook(connection: Connection, invocation: dict[str, Any]) -> None:
            nonlocal lost
            if len(server.connections) == 2 and not lost:
                lost = True
                if close == 'abort':
                    connection.abort()
                else:
                    await connection.send({'type': 7, 'error': CLOSE_ERROR})
                    await connection.ws.close()
                return
            await server.confirm(connection, invocation)

        server.invocation_hook = invocation_hook
        tzkt._subscriptions.add(HeadSubscription())
        async with realtime(tzkt) as task:
            await resubscribe(tzkt)
            server.connections[-1].abort()
            assert await wait_until(lambda: bool(tzkt._subscriptions.missing_subscriptions), 5)

            # NOTE: The completion for the second connection never arrives
            await resubscribe(tzkt)
            assert lost
            assert server.connections[-1].invocations
            assert not task.done(), f'Realtime loop died: {task.exception()!r}'


async def test_subscribe_while_disconnected() -> None:
    async with fake_tzkt() as (server, tzkt):
        status: int | None = None

        async def negotiate_hook(request: web.Request) -> web.StreamResponse | None:
            return web.Response(status=status) if status else None

        server.negotiate_hook = negotiate_hook
        tzkt._subscriptions.add(HeadSubscription())
        async with realtime(tzkt) as task:
            await resubscribe(tzkt)

            # NOTE: TzKT is down behind a proxy for longer than the connection timeout
            status = 502
            server.connections[-1].abort()
            assert await wait_until(lambda: bool(tzkt._subscriptions.missing_subscriptions), 5)
            for _ in range(3):
                await subscribe(tzkt, 2)
            assert tzkt._subscriptions.missing_subscriptions

            status = None
            await resubscribe(tzkt)
            assert len(server.connections) == 2
            assert not task.done(), f'Realtime loop died: {task.exception()!r}'


async def test_sync_level_kept_on_disconnect() -> None:
    async with fake_tzkt() as (_, tzkt):
        transactions = TransactionSubscription(address='KT1PDrBE59Zmxnb8vXRgRAG1XmvTMTs5EDHU')
        tzkt.set_sync_level(None, LEVEL)
        tzkt._subscriptions.add(HeadSubscription())
        tzkt._subscriptions.add(transactions)
        tzkt.set_sync_level(HeadSubscription(), LEVEL + 1)
        tzkt.set_sync_level(transactions, LEVEL + 1)

        await tzkt._on_connected()
        await tzkt._on_disconnected()
        assert tzkt._subscriptions.missing_subscriptions == {HeadSubscription(), transactions}
        assert tzkt.get_sync_level(HeadSubscription()) == LEVEL
        assert tzkt.get_sync_level(transactions) == LEVEL

        # NOTE: Operations are confirmed and arrive before the head subscription is restored
        tzkt.set_sync_level(transactions, LEVEL + 2)
        await tzkt._on_message(TezosTzktMessageType.operation, [{'type': 1, 'state': LEVEL + 2, 'data': []}])
        assert tzkt.get_channel_level(TezosTzktMessageType.operation) == LEVEL + 2
