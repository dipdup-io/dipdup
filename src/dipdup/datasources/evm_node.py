import asyncio
import time
from asyncio import Queue
from collections import defaultdict
from collections.abc import Awaitable
from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from uuid import uuid4

import pysignalr
import pysignalr.exceptions
from pysignalr.messages import CompletionMessage
from web3 import AsyncWeb3
from web3.middleware.async_cache import async_construct_simple_cache_middleware
from web3.providers.async_base import AsyncJSONBaseProvider
from web3.utils.caching import SimpleCache

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
from dipdup.performance import caches
from dipdup.performance import metrics
from dipdup.pysignalr import Message
from dipdup.pysignalr import WebsocketMessage
from dipdup.pysignalr import WebsocketProtocol
from dipdup.pysignalr import WebsocketTransport
from dipdup.utils import Watchdog

WEB3_CACHE_SIZE = 256
POLL_INTERVAL = 5


EmptyCallback = Callable[[], Awaitable[None]]
HeadCallback = Callable[['EvmNodeDatasource', EvmNodeHeadData], Awaitable[None]]
LogsCallback = Callable[['EvmNodeDatasource', EvmNodeLogData], Awaitable[None]]
SyncingCallback = Callable[['EvmNodeDatasource', EvmNodeSyncingData], Awaitable[None]]
RollbackCallback = Callable[['IndexDatasource[Any]', MessageType, int, int], Awaitable[None]]


@dataclass
class NodeHead:
    event: asyncio.Event = field(default_factory=asyncio.Event)
    hash: str | None = None
    timestamp: int | None = None


class EvmNodeDatasource(IndexDatasource[EvmNodeDatasourceConfig]):
    _default_http_config = HttpConfig(
        batch_size=32,
        ratelimit_sleep=30,
    )

    def __init__(self, config: EvmNodeDatasourceConfig, merge_subscriptions: bool = False) -> None:
        super().__init__(config, merge_subscriptions)
        self._web3_client: AsyncWeb3 | None = None
        self._ws_client: WebsocketTransport | None = None
        self._requests: dict[str, tuple[asyncio.Event, Any]] = {}
        self._subscription_ids: dict[str, EvmNodeSubscription] = {}
        self._logs_queue: Queue[dict[str, Any]] = Queue()
        self._heads: defaultdict[int, NodeHead] = defaultdict(NodeHead)
        self._watchdog: Watchdog = Watchdog(self._http_config.connection_timeout)

        self._on_connected_callbacks: set[EmptyCallback] = set()
        self._on_disconnected_callbacks: set[EmptyCallback] = set()
        self._on_rollback_callbacks: set[RollbackCallback] = set()
        self._on_head_callbacks: set[HeadCallback] = set()
        self._on_logs_callbacks: set[LogsCallback] = set()
        self._on_syncing_callbacks: set[SyncingCallback] = set()

    @property
    def web3(self) -> AsyncWeb3:
        if not self._web3_client:
            raise FrameworkException('web3 client is not initialized; is datasource running?')
        return self._web3_client

    async def initialize(self) -> None:
        web3_cache = SimpleCache(WEB3_CACHE_SIZE)
        caches.add_plain(web3_cache._data, f'{self.name}:web3_cache')

        class MagicWeb3Provider(AsyncJSONBaseProvider):
            async def make_request(_, method: str, params: list[Any]) -> Any:
                return await self._jsonrpc_request(
                    method,
                    params,
                    raw=True,
                    ws=False,
                )

        self._web3_client = AsyncWeb3(
            provider=MagicWeb3Provider(),
        )
        self._web3_client.middleware_onion.add(
            await async_construct_simple_cache_middleware(web3_cache),
            'cache',
        )

        level = await self.get_head_level()
        self.set_sync_level(None, level)

    async def run(self) -> None:
        if self.realtime:
            await asyncio.gather(
                self._ws_loop(),
                self._log_processor_loop(),
                self._watchdog.run(),
            )
        else:
            while True:
                level = await self.get_head_level()
                self.set_sync_level(None, level)
                await asyncio.sleep(POLL_INTERVAL)

    async def _log_processor_loop(self) -> None:
        while True:
            log_json = await self._logs_queue.get()
            level = int(log_json['blockNumber'], 16)

            try:
                await asyncio.wait_for(
                    self._heads[level].event.wait(),
                    timeout=self._http_config.connection_timeout,
                )
            except TimeoutError as e:
                msg = f'Head for level {level} not received in {self._http_config.connection_timeout} seconds'
                raise FrameworkException(msg) from e
            timestamp = self._heads[level].timestamp
            if timestamp is None:
                raise FrameworkException('Head received but timestamp is None')
            log = EvmNodeLogData.from_json(log_json, timestamp)
            await self.emit_logs(log)

    async def _ws_loop(self) -> None:
        self._logger.info('Establishing realtime connection')
        client = self._get_ws_client()
        retry_sleep = self._http_config.retry_sleep

        for _ in range(1, self._http_config.retry_count + 1):
            try:
                await client.run()
            except pysignalr.exceptions.ConnectionError as e:
                self._logger.error('Websocket connection error: %s', e)
                await self.emit_disconnected()
                await asyncio.sleep(retry_sleep)
                retry_sleep *= self._http_config.retry_multiplier

        raise DatasourceError('Websocket connection failed', self.name)

    @property
    def realtime(self) -> bool:
        return self._config.ws_url is not None

    async def subscribe(self) -> None:
        if not self.realtime:
            return

        missing_subscriptions = self._subscriptions.missing_subscriptions
        if not missing_subscriptions:
            return

        self._logger.info('Subscribing to %s channels', len(missing_subscriptions))
        for subscription in missing_subscriptions:
            if isinstance(subscription, EvmNodeSubscription):
                await self._subscribe(subscription)

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

    async def get_block_by_level(self, block_number: int, full_transactions: bool = False) -> dict[str, Any]:
        return await self._jsonrpc_request('eth_getBlockByNumber', [hex(block_number), full_transactions])  # type: ignore[no-any-return]

    async def get_logs(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        return await self._jsonrpc_request('eth_getLogs', [params])  # type: ignore[no-any-return]

    async def get_head_level(self) -> int:
        return int((await self._jsonrpc_request('eth_blockNumber', [])), 16)

    async def _subscribe(self, subscription: EvmNodeSubscription) -> None:
        self._logger.debug('Subscribing to %s', subscription)
        response = await self._jsonrpc_request(
            method='eth_subscribe',
            params=subscription.get_params(),
            ws=True,
        )
        self._subscription_ids[response] = subscription
        # NOTE: Is's likely unnecessary and/or unreliable, but node doesn't return sync level.
        level = await self.get_head_level()
        self._subscriptions.set_sync_level(subscription, level)

    async def _jsonrpc_request(
        self,
        method: str,
        params: Any,
        raw: bool = False,
        ws: bool = False,
    ) -> Any:
        request_id = uuid4().hex
        request = {
            'jsonrpc': '2.0',
            'id': request_id,
            'method': method,
            'params': params,
        }

        if ws:
            started_at = time.time()
            namespace = f'{self._config.name}.ws'
            event = asyncio.Event()
            self._requests[request_id] = (event, None)

            message = WebsocketMessage(request)
            client = self._get_ws_client()

            async def _request() -> None:
                await client.send(message)
                await event.wait()

            await asyncio.wait_for(
                _request(),
                timeout=self._http_config.request_timeout,
            )
            data = self._requests[request_id][1]
            del self._requests[request_id]

            metrics and metrics.inc(f'{namespace}:time_in_requests', (time.time() - started_at) / 60)
            metrics and metrics.inc(f'{namespace}:requests_total', 1.0)
        else:
            data = await self.request(
                method='post',
                url='',
                json=request,
            )

        if raw:
            return data

        if 'error' in data:
            raise DatasourceError(data['error']['message'], self.name)
        return data['result']

    async def _on_message(self, message: Message) -> None:
        # NOTE: pysignalr will eventually get a raw client
        if not isinstance(message, WebsocketMessage):
            raise FrameworkException(f'Unknown message type: {type(message)}')

        data = message.data
        self._watchdog.reset()

        if 'id' in data:
            request_id = data['id']
            self._logger.debug('Received response for request %s', request_id)
            if request_id not in self._requests:
                raise DatasourceError(f'Unknown request ID: {data["id"]}', self.name)

            event = self._requests[request_id][0]
            # NOTE: Don't unpack; processed later
            self._requests[request_id] = (event, data)
            event.set()
        elif 'method' in data:
            if data['method'] == 'eth_subscription':
                subscription_id = data['params']['subscription']
                if subscription_id not in self._subscription_ids:
                    raise FrameworkException(f'{self.name}: Unknown subscription ID: {subscription_id}')
                subscription = self._subscription_ids[subscription_id]
                self._logger.debug('Received a message from channel %s', subscription_id)
                await self._handle_subscription(subscription, data['params']['result'])
            else:
                raise DatasourceError(f'Unknown method: {data["method"]}', self.name)
        else:
            raise DatasourceError(f'Unknown message: {data}', self.name)

    async def _handle_subscription(self, subscription: EvmNodeSubscription, data: Any) -> None:
        if isinstance(subscription, EvmNodeNewHeadsSubscription):
            head = EvmNodeHeadData.from_json(data)
            level = head.number

            known_hash = self._heads[level].hash
            if known_hash not in (head.hash, None):
                await self.emit_rollback(
                    MessageType(),
                    from_level=max(self._heads.keys() or (level,)),
                    to_level=level - 1,
                )

            self._heads[level].hash = head.hash
            self._heads[level].timestamp = head.timestamp
            await self.emit_head(head)
            self._heads[level].event.set()

        elif isinstance(subscription, EvmNodeLogsSubscription):
            # NOTE: Processed in _log_processor_loop to avoid blocking WebSocket while waiting for head
            await self._logs_queue.put(data)

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

        self._logger.debug('Creating Websocket client')

        url = self._config.ws_url
        if not url:
            raise FrameworkException('Spawning node datasource, but `ws_url` is not set')
        self._ws_client = WebsocketTransport(
            url=url,
            protocol=WebsocketProtocol(),
            callback=self._on_message,
            skip_negotiation=True,
            connection_timeout=self._http_config.connection_timeout,
        )

        self._ws_client.on_open(self._on_connected)
        self._ws_client.on_close(self._on_disconnected)
        self._ws_client.on_error(self._on_error)

        return self._ws_client
