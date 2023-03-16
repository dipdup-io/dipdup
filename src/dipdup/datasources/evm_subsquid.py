import asyncio
import zipfile
from io import BytesIO
from typing import Any
from typing import AsyncIterator
from typing import TypedDict
from uuid import uuid4

import pyarrow.ipc  # type: ignore[import]
from typing_extensions import NotRequired

from dipdup.config import HttpConfig
from dipdup.config import ResolvedIndexConfigU
from dipdup.config.evm_subsquid import SubsquidDatasourceConfig
from dipdup.datasources import IndexDatasource
from dipdup.exceptions import DatasourceError
from dipdup.exceptions import FrameworkException
from dipdup.models.evm_subsquid import ArchiveSubscription
from dipdup.models.evm_subsquid import NodeHeadSubscription
from dipdup.models.evm_subsquid import NodeSubscription
from dipdup.models.evm_subsquid import SubsquidEventData
from dipdup.pysignalr import Message
from dipdup.pysignalr import WebsocketMessage
from dipdup.pysignalr import WebsocketProtocol
from dipdup.pysignalr import WebsocketTransport

FieldMap = dict[str, bool]


class FieldSelection(TypedDict):
    block: NotRequired[FieldMap]
    transaction: NotRequired[FieldMap]
    log: NotRequired[FieldMap]


class LogFilter(TypedDict):
    address: NotRequired[list[str]]
    topics: NotRequired[list[list[str]]]
    fieldSelection: NotRequired[FieldSelection]


class TxFilter(TypedDict):
    to: NotRequired[list[str]]
    sighash: NotRequired[list[str]]


class Query(TypedDict):
    logs: NotRequired[list[LogFilter]]
    transactions: NotRequired[list[TxFilter]]
    fromBlock: NotRequired[int]
    toBlock: NotRequired[int]


_log_fields: FieldSelection = {
    'log': {
        'address': True,
        'blockNumber': True,
        'data': True,
        'topics': True,
    },
}


def unpack_data(content: bytes) -> dict[str, list[dict[str, Any]]]:
    data = {}
    with zipfile.ZipFile(BytesIO(content), 'r') as arch:
        for item in arch.filelist:  # The set of files depends on requested data
            with arch.open(item) as f, pyarrow.ipc.open_stream(f) as reader:
                table: pyarrow.Table = reader.read_all()
                data[item.filename] = table.to_pylist()
    return data


class _NodeDatasource(IndexDatasource[SubsquidDatasourceConfig]):
    _default_http_config = HttpConfig()

    def __init__(self, config: SubsquidDatasourceConfig, merge_subscriptions: bool = False) -> None:
        super().__init__(config, merge_subscriptions)
        self._url = config.node_url
        self._ws_client: WebsocketTransport | None = None
        self._requests: dict[str, tuple[asyncio.Event, Any]] = {}
        self._subscription_ids: dict[str, NodeSubscription] = {}

    async def initialize(self) -> None:
        pass

    async def run(self) -> None:
        if not self._config.node_url:
            return

        client = self._get_ws_client()
        await client.run()

    async def subscribe(self) -> None:
        missing_subscriptions = self._subscriptions.missing_subscriptions
        if not missing_subscriptions:
            return

        self._logger.info('Subscribing to %s channels', len(missing_subscriptions))
        for subscription in missing_subscriptions:
            if not isinstance(subscription, NodeSubscription):
                raise FrameworkException(f'Expected NodeSubscription, got {subscription}')
            await self._subscribe(subscription)
        self._logger.info('Subscribed to %s channels', len(missing_subscriptions))

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
            url = self._config.node_ws_url
            if not url:
                raise FrameworkException('Node URL is missing')

            self._ws_client = WebsocketTransport(
                url=url,
                protocol=WebsocketProtocol(),
                callback=self._on_message,
                skip_negotiation=True,
            )
        return self._ws_client


class SubsquidDatasource(IndexDatasource[SubsquidDatasourceConfig]):
    _default_http_config = HttpConfig()

    def __init__(self, config: SubsquidDatasourceConfig) -> None:
        super().__init__(config, False)
        self._node = _NodeDatasource(config)

    async def run(self) -> None:
        await self._node.run()

        # FIXME: No true realtime yet
        # while True:
        #     await asyncio.sleep(1)
        #     await self.update_head()

    async def subscribe(self) -> None:
        if self._node:
            await self._node.subscribe()

    async def add_index(self, index_config: ResolvedIndexConfigU) -> None:
        """Register index config in internal mappings and matchers. Find and register subscriptions."""
        for subscription in index_config.subscriptions:
            if isinstance(subscription, ArchiveSubscription):
                self._subscriptions.add(subscription)
            elif isinstance(subscription, NodeSubscription):
                self._node._subscriptions.add(subscription)
            else:
                raise FrameworkException(f'Unknown subscription type: {type(subscription)}')

    async def iter_event_logs(
        self,
        addresses: set[str],
        topics: set[str],
        first_level: int,
        last_level: int,
    ) -> AsyncIterator[tuple[SubsquidEventData, ...]]:
        current_level = first_level

        while current_level <= last_level:
            query: Query = {
                'logs': [
                    {
                        'address': list(addresses or ()),
                        'topics': [list(topics or ())],
                        'fieldSelection': _log_fields,
                    }
                ],
                'fromBlock': current_level,
                'toBlock': last_level,
            }

            response: dict[str, Any] = await self.request(
                'post',
                url='query',
                json=query,
            )

            current_level = response['nextBlock']
            await self.update_head(response['archiveHeight'])

            logs: list[SubsquidEventData] = []
            for level in response['data']:
                for transaction in level:
                    for raw_log in transaction['logs']:
                        logs.append(
                            SubsquidEventData.from_json(raw_log),
                        )
            yield tuple(logs)

    async def initialize(self) -> None:
        await self.update_head()

    async def update_head(self, level: int | None = None) -> None:
        if level is None:
            response = await self.request('get', 'height')
            level = response.get('height')

        if level is None:
            raise DatasourceError('Archive is not ready yet', self.name)

        # FIXME: Random subscriptions
        self._node._subscriptions.add(NodeHeadSubscription())
        self._subscriptions.add(NodeHeadSubscription())

        self.set_sync_level(None, level)
        self._node.set_sync_level(None, level)
