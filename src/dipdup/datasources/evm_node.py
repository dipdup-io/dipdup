import asyncio
from collections import defaultdict
from typing import Any
from typing import Awaitable
from typing import Callable
from uuid import uuid4

from pysignalr.messages import CompletionMessage
from web3 import AsyncHTTPProvider
from web3 import AsyncWeb3

from dipdup.config import HttpConfig
from dipdup.config.evm_node import EvmNodeDatasourceConfig
from dipdup.datasources import IndexDatasource
from dipdup.exceptions import DatasourceError
from dipdup.exceptions import FrameworkException
from dipdup.models import MessageType
from dipdup.models.evm_node import EvmNodeHeadData
from dipdup.models.evm_node import EvmNodeLogData
from dipdup.models.evm_node import EvmNodeLogsSubscription
from dipdup.models.evm_node import EvmNodeNewHeadsSubscription
from dipdup.models.evm_node import EvmNodeSubscription
from dipdup.models.evm_node import EvmNodeSyncingData
from dipdup.performance import profiler
from dipdup.pysignalr import Message
from dipdup.pysignalr import WebsocketMessage
from dipdup.pysignalr import WebsocketProtocol
from dipdup.pysignalr import WebsocketTransport

EmptyCallback = Callable[[], Awaitable[None]]
HeadCallback = Callable[['EvmNodeDatasource', EvmNodeHeadData], Awaitable[None]]
LogsCallback = Callable[['EvmNodeDatasource', EvmNodeLogData], Awaitable[None]]
SyncingCallback = Callable[['EvmNodeDatasource', EvmNodeSyncingData], Awaitable[None]]
RollbackCallback = Callable[['IndexDatasource', MessageType, int, int], Awaitable[None]]


class EvmNodeDatasource(IndexDatasource[EvmNodeDatasourceConfig]):
    # TODO: Make dynamic
    _default_http_config = HttpConfig()

    def __init__(self, config: EvmNodeDatasourceConfig, merge_subscriptions: bool = False) -> None:
        super().__init__(config, merge_subscriptions)
        self._web3_client: AsyncWeb3 = AsyncWeb3(AsyncHTTPProvider(config.url))
        self._ws_client: WebsocketTransport | None = None
        self._requests: dict[str, tuple[asyncio.Event, Any]] = {}
        self._subscription_ids: dict[str, EvmNodeSubscription] = {}
        self._head_hashes: dict[int, str] = {}
        self._head_events: defaultdict[int, asyncio.Event] = defaultdict(asyncio.Event)

        self._on_connected_callbacks: set[EmptyCallback] = set()
        self._on_disconnected_callbacks: set[EmptyCallback] = set()
        self._on_rollback_callbacks: set[RollbackCallback] = set()
        self._on_head_callbacks: set[HeadCallback] = set()
        self._on_logs_callbacks: set[LogsCallback] = set()
        self._on_syncing_callbacks: set[SyncingCallback] = set()

    @property
    def web3(self) -> AsyncWeb3:
        # FIXME: temporary, remove after implementing pysignalr transport
        profiler and profiler.inc('web3_touched_total', 1.0)
        return self._web3_client

    async def initialize(self) -> None:
        pass

    async def run(self) -> None:
        client = self._get_ws_client()
        await client.run()

    async def subscribe(self) -> None:
        missing_subscriptions = self._subscriptions.missing_subscriptions
        if not missing_subscriptions:
            return

        self._logger.info('Subscribing to %s channels', len(missing_subscriptions))
        for subscription in missing_subscriptions:
            if isinstance(subscription, EvmNodeSubscription):
                await self._subscribe(subscription)

        self._logger.info('Subscribed to %s channels', len(missing_subscriptions))

    async def emit_rollback(self, type_: MessageType, from_level: int, to_level: int) -> None:
        for fn in self._on_rollback_callbacks:
            await fn(self, type_, from_level, to_level)

    async def emit_connected(self) -> None:
        for fn in self._on_connected_callbacks:
            await fn()

    async def emit_disconnected(self) -> None:
        for fn in self._on_disconnected_callbacks:
            await fn()

    async def emit_head(self, head: EvmNodeHeadData) -> None:
        for fn in self._on_head_callbacks:
            await fn(self, head)

    async def emit_logs(self, logs: EvmNodeLogData) -> None:
        for fn in self._on_logs_callbacks:
            await fn(self, logs)

    async def emit_syncing(self, syncing: EvmNodeSyncingData) -> None:
        for fn in self._on_syncing_callbacks:
            await fn(self, syncing)

    def call_on_head(self, fn: HeadCallback) -> None:
        self._on_head_callbacks.add(fn)

    def call_on_logs(self, fn: LogsCallback) -> None:
        self._on_logs_callbacks.add(fn)

    def call_on_syncing(self, fn: SyncingCallback) -> None:
        self._on_syncing_callbacks.add(fn)

    def call_on_connected(self, fn: EmptyCallback) -> None:
        self._on_connected_callbacks.add(fn)

    def call_on_disconnected(self, fn: EmptyCallback) -> None:
        self._on_disconnected_callbacks.add(fn)

    async def get_block_by_hash(self, block_hash: str) -> dict[str, Any]:
        return await self._jsonrpc_request('eth_getBlockByHash', [block_hash, True])  # type: ignore[no-any-return]

    async def get_block_by_level(self, block_number: int) -> dict[str, Any]:
        return await self._jsonrpc_request('eth_getBlockByNumber', [hex(block_number), True])  # type: ignore[no-any-return]

    async def get_logs(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        return await self._jsonrpc_request('eth_getLogs', [params])  # type: ignore[no-any-return]

    async def get_head_level(self) -> int:
        return int((await self._jsonrpc_request('eth_blockNumber', [])), 16)

    async def _subscribe(self, subscription: EvmNodeSubscription) -> None:
        self._logger.debug('Subscribing to %s', subscription)
        response = await self._jsonrpc_request(
            'eth_subscribe',
            subscription.get_params(),
        )
        self._subscription_ids[response] = subscription
        # NOTE: This is possibly unnecessary and/or unreliable, but node doesn't return sync level on subscription.
        level = await self.get_head_level()
        self._subscriptions.set_sync_level(subscription, level)

    async def _jsonrpc_request(
        self,
        method: str,
        params: Any,
    ) -> Any:
        request_id = uuid4().hex
        request = {
            'jsonrpc': '2.0',
            'id': request_id,
            'method': method,
            'params': params,
        }
        event = asyncio.Event()
        self._requests[request_id] = (event, None)

        message = WebsocketMessage(request)
        client = self._get_ws_client()
        await client.send(message)

        await event.wait()
        data = self._requests[request_id][1]
        del self._requests[request_id]
        return data

    async def _on_message(self, message: Message) -> None:
        # NOTE: pysignalr will eventually get a raw client
        if not isinstance(message, WebsocketMessage):
            raise FrameworkException(f'Unknown message type: {type(message)}')

        data = message.data

        if 'id' in data:
            if 'error' in data:
                raise DatasourceError(f'JSON-RPC error: {data["error"]}', self.name)

            request_id = data['id']
            if request_id not in self._requests:
                raise DatasourceError(f'Unknown request ID: {data["id"]}', self.name)

            event = self._requests[request_id][0]
            self._requests[request_id] = (event, data['result'])
            event.set()
        elif 'method' in data:
            if data['method'] == 'eth_subscription':
                subscription_id = data['params']['subscription']
                subscription = self._subscription_ids[subscription_id]
                await self._handle_subscription(subscription, data['params']['result'])

            else:
                raise DatasourceError(f'Unknown method: {data["method"]}', self.name)
        else:
            raise DatasourceError(f'Unknown message: {data}', self.name)

    async def _handle_subscription(self, subscription: EvmNodeSubscription, data: Any) -> None:
        msg_type = MessageType()

        if isinstance(subscription, EvmNodeNewHeadsSubscription):
            head = EvmNodeHeadData.from_json(data)
            level = int(head.number, 16)

            known_hash = self._head_hashes.get(level, None)
            current_level = max(self._head_hashes.keys() or (level,))
            self._head_hashes[level] = head.hash
            if known_hash != head.hash:
                await self.emit_rollback(msg_type, from_level=current_level, to_level=level - 1)

            await self.emit_head(head)
            self._head_events[level].set()

        elif isinstance(subscription, EvmNodeLogsSubscription):
            logs = EvmNodeLogData.from_json(data)
            level = int(logs.block_number, 16)

            await self._head_events[level].wait()
            await self.emit_logs(logs)

        elif isinstance(subscription, EvmNodeSyncingData):
            syncing = EvmNodeSyncingData.from_json(data)
            await self.emit_syncing(syncing)
        else:
            raise NotImplementedError

    async def _on_error(self, message: CompletionMessage) -> None:
        raise DatasourceError(f'Node error: {message}', self.name)

    async def _on_connected(self) -> None:
        self._logger.info('Realtime connection established')
        # NOTE: Subscribing here will block WebSocket loop, don't do it.
        await self.emit_connected()

    async def _on_disconnected(self) -> None:
        self._logger.info('Realtime connection lost, resetting subscriptions')
        self._subscriptions.reset()
        await self.emit_disconnected()

    def _get_ws_client(self) -> WebsocketTransport:
        if self._ws_client:
            return self._ws_client

        self._logger.info('Creating Websocket client')

        url = self._config.ws_url
        self._ws_client = WebsocketTransport(
            url=url,
            protocol=WebsocketProtocol(),
            callback=self._on_message,
            skip_negotiation=True,
        )

        self._ws_client.on_open(self._on_connected)
        self._ws_client.on_close(self._on_disconnected)
        self._ws_client.on_error(self._on_error)

        return self._ws_client
