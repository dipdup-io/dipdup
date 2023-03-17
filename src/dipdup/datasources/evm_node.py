import asyncio
from typing import Any
from uuid import uuid4

from dipdup.config import HttpConfig
from dipdup.config import ResolvedIndexConfigU
from dipdup.config.evm_node import EvmNodeDatasourceConfig
from dipdup.datasources import IndexDatasource
from dipdup.exceptions import DatasourceError
from dipdup.models.evm_node import NodeSubscription
from dipdup.pysignalr import Message
from dipdup.pysignalr import WebsocketMessage
from dipdup.pysignalr import WebsocketProtocol
from dipdup.pysignalr import WebsocketTransport


class EvmNodeDatasource(IndexDatasource[EvmNodeDatasourceConfig]):
    _default_http_config = HttpConfig()

    def __init__(self, config: EvmNodeDatasourceConfig, merge_subscriptions: bool = False) -> None:
        super().__init__(config, merge_subscriptions)
        self._ws_client: WebsocketTransport | None = None
        self._requests: dict[str, tuple[asyncio.Event, Any]] = {}
        self._subscription_ids: dict[str, NodeSubscription] = {}

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
            if isinstance(subscription, NodeSubscription):
                await self._subscribe(subscription)
        self._logger.info('Subscribed to %s channels', len(missing_subscriptions))

    async def add_index(self, index_config: ResolvedIndexConfigU) -> None:
        """Register index config in internal mappings and matchers. Find and register subscriptions."""
        for subscription in index_config.subscriptions:
            self._subscriptions.add(subscription)

    async def _subscribe(self, subscription: NodeSubscription) -> None:
        self._logger.debug('Subscribing to %s', subscription)
        response = await self._request('eth_subscribe', subscription.get_params())
        self._subscription_ids[response['result']] = subscription
        self._subscriptions.set_sync_level(subscription, 0)

    async def _request(
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
        return self._requests[request_id][1]

    async def _on_message(self, message: Message) -> None:
        if not isinstance(message, WebsocketMessage):
            raise DatasourceError(f'Unknown message type: {type(message)}', self.name)

        data = message.data
        if 'id' in data:
            request_id = data['id']
            if request_id not in self._requests:
                raise DatasourceError(f'Unknown request ID: {data["id"]}', self.name)

            event = self._requests[request_id][0]
            self._requests[request_id] = (event, data)
            event.set()
        elif 'method' in data:
            if data['method'] == 'eth_subscription':
                subscription_id = data['params']['subscription']
                subscription = self._subscription_ids[subscription_id]
                # FIXME: handle subscriptions
                print(subscription_id)
                print(subscription)
                # await self._handle_subscription(subscription, data['params']['result'])
            else:
                raise DatasourceError(f'Unknown method: {data["method"]}', self.name)
        else:
            raise DatasourceError(f'Unknown message: {data}', self.name)

    async def _on_error(self, message: WebsocketMessage) -> None:
        raise DatasourceError(f'Node error: {message.data}', self.name)

    async def _on_open(self) -> None:
        await self.subscribe()

    def _get_ws_client(self) -> WebsocketTransport:
        if self._ws_client is None:
            url = self._config.ws_url
            self._ws_client = WebsocketTransport(
                url=url,
                protocol=WebsocketProtocol(),
                callback=self._on_message,
                skip_negotiation=True,
            )
        return self._ws_client
