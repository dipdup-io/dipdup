import asyncio
import logging
from functools import partial
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple, Union

from aiosignalrcore.hub.base_hub_connection import BaseHubConnection  # type: ignore
from aiosignalrcore.hub_connection_builder import HubConnectionBuilder  # type: ignore
from aiosignalrcore.messages.completion_message import CompletionMessage  # type: ignore
from aiosignalrcore.transport.websockets.connection import ConnectionState  # type: ignore
from tortoise.transactions import in_transaction

from dipdup import __version__
from dipdup.config import (
    ROLLBACK_HANDLER,
    BigMapHandlerConfig,
    BigMapIndexConfig,
    BlockIndexConfig,
    OperationHandlerConfig,
    OperationIndexConfig,
)
from dipdup.datasources.tzkt.cache import BigMapCache, OperationCache
from dipdup.datasources.tzkt.enums import TzktMessageType
from dipdup.datasources.tzkt.proxy import TzktRequestProxy
from dipdup.models import (
    BigMapAction,
    BigMapContext,
    BigMapData,
    BigMapHandlerContext,
    OperationContext,
    OperationData,
    OperationHandlerContext,
)
from dipdup.utils import http_request

TZKT_HTTP_REQUEST_LIMIT = 10000
TZKT_HTTP_REQUEST_SLEEP = 1
OPERATION_FIELDS = (
    "type",
    "id",
    "level",
    "timestamp",
    # "block",
    "hash",
    "counter",
    "initiator",
    "sender",
    "nonce",
    # "gasLimit",
    # "gasUsed",
    # "storageLimit",
    # "storageUsed",
    # "bakerFee",
    # "storageFee",
    # "allocationFee",
    "target",
    "amount",
    "parameter",
    "storage",
    "status",
    # "errors",
    "hasInternals",
    # "quote",
    "diffs,",
)

IndexName = str
Address = str
Path = str
OperationType = str


class TzktDatasource:
    def __init__(self, url: str, cache: bool):
        super().__init__()
        self._url = url.rstrip('/')
        self._logger = logging.getLogger(__name__)
        self._operation_index_by_name: Dict[IndexName, OperationIndexConfig] = {}
        self._big_map_index_by_name: Dict[IndexName, BigMapIndexConfig] = {}
        self._big_map_index_by_address: Dict[Address, BigMapIndexConfig] = {}
        self._callback_lock = asyncio.Lock()
        self._operation_subscriptions: Dict[Address, List[OperationType]] = {}
        self._big_map_subscriptions: Dict[Address, List[Path]] = {}
        self._operations_synchronized = asyncio.Event()
        self._big_maps_synchronized = asyncio.Event()
        self._client: Optional[BaseHubConnection] = None
        self._operation_cache = OperationCache()
        self._big_map_cache = BigMapCache()
        self._rollback_fn: Optional[Callable[[int, int], Awaitable[None]]] = None
        self._proxy = TzktRequestProxy(cache)

    async def add_index(self, index_name: str, index_config: Union[OperationIndexConfig, BigMapIndexConfig, BlockIndexConfig]):
        self._logger.info('Adding index `%s`', index_name)
        if isinstance(index_config, OperationIndexConfig):
            self._operation_index_by_name[index_name] = index_config
            await self._operation_cache.add_index(index_config)

        elif isinstance(index_config, BigMapIndexConfig):
            self._big_map_index_by_name[index_name] = index_config
            await self._big_map_cache.add_index(index_config)

        else:
            raise NotImplementedError(f'Index kind `{index_config.kind}` is not supported')

    def set_rollback_fn(self, fn: Callable[[int, int], Awaitable[None]]) -> None:
        self._rollback_fn = fn

    def _get_client(self) -> BaseHubConnection:
        if self._client is None:
            self._logger.info('Creating websocket client')
            self._client = (
                HubConnectionBuilder()
                .with_url(self._url + '/v1/events')
                .with_automatic_reconnect(
                    {
                        "type": "raw",
                        "keep_alive_interval": 10,
                        "reconnect_interval": 5,
                        "max_attempts": 5,
                    }
                )
            ).build()
            self._client.on_open(self.on_connect)
            self._client.on_error(self.on_error)
            self._client.on('operations', self.on_operation_message)
            self._client.on('bigmaps', self.on_big_map_message)

        return self._client

    async def start(self):
        self._logger.info('Starting datasource')
        rest_only = False

        self._logger.info('Initial synchronizing operation indexes')
        for operation_index_config in self._operation_index_by_name.values():

            if operation_index_config.last_block:
                await self.fetch_operations(operation_index_config.last_block, initial=True)
                rest_only = True
                continue

            for contract in operation_index_config.contracts:
                await self.add_operation_subscription(contract.address)

            latest_block = await self.get_latest_block()
            current_level = latest_block['level']
            state_level = operation_index_config.state.level
            if current_level != state_level:
                await self.fetch_operations(current_level, initial=True)

        self._logger.info('Initial synchronizing big map indexes')
        for big_map_index_config in self._big_map_index_by_name.values():

            if big_map_index_config.last_block:
                await self.fetch_big_maps(big_map_index_config.last_block, initial=True)
                rest_only = True
                continue

            for handler_config in big_map_index_config.handlers:
                for pattern_config in handler_config.pattern:
                    await self.add_big_map_subscription(pattern_config.contract_config.address, pattern_config.path)

            latest_block = await self.get_latest_block()
            current_level = latest_block['level']
            state_level = big_map_index_config.state.level
            if current_level != state_level:
                await self.fetch_big_maps(current_level, initial=True)

        if not rest_only:
            self._logger.info('Starting websocket client')
            await self._get_client().start()

    async def stop(self):
        ...

    async def on_connect(self):
        self._logger.info('Connected to server')
        for address, types in self._operation_subscriptions.items():
            await self.subscribe_to_operations(address, types)
        for address, paths in self._big_map_subscriptions.items():
            for path in paths:
                await self.subscribe_to_big_maps(address, paths)

    def on_error(self, message: CompletionMessage):
        raise Exception(message.error)

    async def subscribe_to_operations(self, address: str, types: List[str]) -> None:
        self._logger.info('Subscribing to %s, %s', address, types)

        while self._get_client().transport.state != ConnectionState.connected:
            await asyncio.sleep(0.1)

        await self._get_client().send(
            'SubscribeToOperations',
            [
                {
                    'address': address,
                    'types': ','.join(types),
                }
            ],
        )

    async def subscribe_to_big_maps(self, address: Address, path: Path) -> None:
        self._logger.info('Subscribing to %s, %s', address, path)

    async def _fetch_operations(self, addresses: List[str], offset: int, first_level: int, last_level: int) -> List[Dict[str, Any]]:
        self._logger.info('Fetching levels %s-%s with offset %s', first_level, last_level, offset)

        operations = await self._proxy.http_request(
            'get',
            url=f'{self._url}/v1/operations/transactions',
            params={
                "sender.in": ','.join(addresses),
                "offset": offset,
                "limit": TZKT_HTTP_REQUEST_LIMIT,
                "level.gt": first_level,
                "level.le": last_level,
                "select": ','.join(OPERATION_FIELDS),
                "status": "applied",
            },
        )

        target_operations = await self._proxy.http_request(
            'get',
            url=f'{self._url}/v1/operations/transactions',
            params={
                "target.in": ','.join(addresses),
                "offset": offset,
                "limit": TZKT_HTTP_REQUEST_LIMIT,
                "level.gt": first_level,
                "level.le": last_level,
                "select": ','.join(OPERATION_FIELDS),
                "status": "applied",
            },
        )

        sender_operation_keys = {op['id'] for op in operations}
        for op in target_operations:
            if op['id'] not in sender_operation_keys:
                operations.append(op)

        operations = sorted(operations, key=lambda op: op['id'])

        self._logger.info('%s operations fetched', len(operations))
        self._logger.debug(operations)
        return operations

    async def fetch_operations(self, last_level: int, initial: bool = False) -> None:
        async def _process_level_operations(operations) -> None:
            self._logger.info('Processing %s operations of level %s', len(operations), operations[0]['level'])
            await self.on_operation_message(
                message=[
                    {
                        'type': TzktMessageType.DATA.value,
                        'data': operations,
                    },
                ],
                sync=True,
            )

        self._logger.info('Fetching operations prior to level %s', last_level)
        for index_config in self._operation_index_by_name.values():

            level = index_config.state.level

            operations = []
            offset = 0
            addresses = [c.address for c in index_config.contract_configs]

            while True:
                fetched_operations = await self._fetch_operations(addresses, offset, level, last_level)
                operations += fetched_operations

                while True:
                    for i in range(len(operations) - 1):
                        if operations[i]['level'] != operations[i + 1]['level']:
                            await _process_level_operations(operations[: i + 1])
                            operations = operations[i + 1 :]
                            break
                    else:
                        break

                if len(fetched_operations) < TZKT_HTTP_REQUEST_LIMIT:
                    break

                offset += TZKT_HTTP_REQUEST_LIMIT
                self._logger.info('Sleeping %s seconds before fetching next batch', TZKT_HTTP_REQUEST_SLEEP)
                await asyncio.sleep(TZKT_HTTP_REQUEST_SLEEP)

            if operations:
                await _process_level_operations(operations)

        if not initial:
            self._operations_synchronized.set()

    async def _fetch_big_maps(
        self, addresses: List[Address], paths: List[Path], offset: int, first_level: int, last_level: int
    ) -> List[Dict[str, Any]]:
        self._logger.info('Fetching levels %s-%s with offset %s', first_level, last_level, offset)

        big_maps = await self._proxy.http_request(
            'get',
            url=f'{self._url}/v1/bigmaps/updates',
            params={
                "contract.in": ",".join(addresses),
                "paths.in": ",".join(paths),
                "offset": offset,
                "limit": TZKT_HTTP_REQUEST_LIMIT,
                "level.gt": first_level,
                "level.le": last_level,
            },
        )

        self._logger.info('%s big map updates fetched', len(big_maps))
        self._logger.debug(big_maps)
        return big_maps

    async def fetch_big_maps(self, last_level: int, initial: bool = False) -> None:
        async def _process_level_big_maps(big_maps):
            self._logger.info('Processing %s big map updates of level %s', len(big_maps), big_maps[0]['level'])
            await self.on_big_map_message(
                message=[
                    {
                        'type': TzktMessageType.DATA.value,
                        'data': big_maps,
                    },
                ],
                sync=True,
            )

        self._logger.info('Fetching big map updates prior to level %s', last_level)
        for index_config in self._big_map_index_by_name.values():

            level = index_config.state.level

            big_maps = []
            offset = 0
            addresses, paths = set(), set()
            for handler_config in index_config.handlers:
                for pattern_config in handler_config.pattern:
                    addresses.add(pattern_config.contract_config.address)
                    paths.add(pattern_config.path)

            while True:
                fetched_big_maps = await self._fetch_big_maps(list(addresses), list(paths), offset, level, last_level)
                big_maps += fetched_big_maps

                while True:
                    for i in range(len(big_maps) - 1):
                        if big_maps[i]['level'] != big_maps[i + 1]['level']:
                            await _process_level_big_maps(big_maps[: i + 1])
                            big_maps = big_maps[i + 1 :]
                            break
                    else:
                        break

                if len(fetched_big_maps) < TZKT_HTTP_REQUEST_LIMIT:
                    break

                offset += TZKT_HTTP_REQUEST_LIMIT
                self._logger.info('Sleeping %s seconds before fetching next batch', TZKT_HTTP_REQUEST_SLEEP)
                await asyncio.sleep(TZKT_HTTP_REQUEST_SLEEP)

            if big_maps:
                await _process_level_big_maps(big_maps)

        if not initial:
            self._big_maps_synchronized.set()

    async def fetch_jsonschemas(self, address: str) -> Dict[str, Any]:
        self._logger.info('Fetching jsonschemas for address `%s', address)
        jsonschemas = await self._proxy.http_request(
            'get',
            url=f'{self._url}/v1/contracts/{address}/interface',
        )
        self._logger.debug(jsonschemas)
        return jsonschemas

    async def on_operation_message(
        self,
        message: List[Dict[str, Any]],
        sync=False,
    ) -> None:
        self._logger.info('Got operation message')
        self._logger.debug('%s', message)

        for item in message:
            message_type = TzktMessageType(item['type'])

            if message_type == TzktMessageType.STATE:
                level = item['state']
                self._logger.info('Got state message, current level %s, index level %s', level, self._operation_cache.level)
                await self.fetch_operations(level)

            elif message_type == TzktMessageType.DATA:
                if not sync and not self._operations_synchronized.is_set():
                    self._logger.info('Waiting until synchronization is complete')
                    await self._operations_synchronized.wait()
                    self._logger.info('Synchronization is complete, processing websocket message')

                self._logger.info('Acquiring callback lock')
                async with self._callback_lock:
                    for operation_json in item['data']:
                        operation = self.convert_operation(operation_json)
                        if operation.type != 'transaction':
                            continue
                        if operation.status != 'applied':
                            continue
                        await self._operation_cache.add(operation)

                    async with in_transaction():
                        await self._operation_cache.process(self.on_operation_match)

            elif message_type == TzktMessageType.REORG:
                if self._rollback_fn is None:
                    raise RuntimeError('rollback_fn is not set')
                self._logger.info('Got reorg message, calling `%s` handler', ROLLBACK_HANDLER)
                # NOTE: It doesn't matter which index to get
                from_level = list(self._operation_index_by_name.values())[0].state.level
                to_level = item['state']
                await self._rollback_fn(from_level, to_level)

            else:
                self._logger.warning('%s is not supported', message_type)

    async def on_big_map_message(
        self,
        message: List[Dict[str, Any]],
        sync=False,
    ) -> None:
        self._logger.info('Got big map message')
        self._logger.debug('%s', message)

        for item in message:
            message_type = TzktMessageType(item['type'])

            if message_type == TzktMessageType.STATE:
                level = item['state']
                self._logger.info('Got state message, current level %s, index level %s', level, self._operation_cache.level)
                await self.fetch_big_maps(level)

            elif message_type == TzktMessageType.DATA:
                if not sync and not self._big_maps_synchronized.is_set():
                    self._logger.info('Waiting until synchronization is complete')
                    await self._big_maps_synchronized.wait()
                    self._logger.info('Synchronization is complete, processing websocket message')

                self._logger.info('Acquiring callback lock')
                async with self._callback_lock:
                    for big_map_json in item['data']:
                        big_map = self.convert_big_map(big_map_json)
                        await self._big_map_cache.add(big_map)

                    async with in_transaction():
                        await self._big_map_cache.process(self.on_big_map_match)

            elif message_type == TzktMessageType.REORG:
                if self._rollback_fn is None:
                    raise RuntimeError('rollback_fn is not set')
                self._logger.info('Got reorg message, calling `%s` handler', ROLLBACK_HANDLER)
                # NOTE: It doesn't matter which index to get
                from_level = list(self._big_map_index_by_name.values())[0].state.level
                to_level = item['state']
                await self._rollback_fn(from_level, to_level)

            else:
                self._logger.warning('%s is not supported', message_type)

    async def add_operation_subscription(self, address: str, types: Optional[List[str]] = None) -> None:
        if types is None:
            types = ['transaction']
        if address not in self._operation_subscriptions:
            self._operation_subscriptions[address] = types

    async def add_big_map_subscription(self, address: str, path: str) -> None:
        if address not in self._big_map_subscriptions:
            self._big_map_subscriptions[address] = []
        self._big_map_subscriptions[address].append('path')

    async def on_operation_match(
        self,
        index_config: OperationIndexConfig,
        handler_config: OperationHandlerConfig,
        matched_operations: List[OperationData],
        operations: List[OperationData],
    ):
        handler_context = OperationHandlerContext(
            operations=operations,
            template_values=index_config.template_values,
        )
        args: List[Union[OperationHandlerContext, OperationContext]] = [handler_context]
        for pattern_config, operation in zip(handler_config.pattern, matched_operations):

            parameter_type = pattern_config.parameter_type_cls
            parameter = parameter_type.parse_obj(operation.parameter_json)

            storage_type = pattern_config.storage_type_cls
            storage = operation.get_merged_storage(storage_type)

            operation_context = OperationContext(
                data=operation,
                parameter=parameter,
                storage=storage,
            )
            args.append(operation_context)

        await handler_config.callback_fn(*args)

    async def on_big_map_match(
        self,
        index_config: BigMapIndexConfig,
        handler_config: BigMapHandlerConfig,
        matched_big_maps: List[List[BigMapData]],
    ):
        handler_context = BigMapHandlerContext(
            template_values=index_config.template_values,
        )
        args: List[Union[BigMapHandlerContext, List[BigMapContext]]] = [handler_context]
        for matched_big_map_group, pattern_config in zip(matched_big_maps, handler_config.pattern):
            big_map_contexts = []
            for big_map in matched_big_map_group:

                try:
                    action = BigMapAction(big_map.action)
                except ValueError:
                    continue

                key_type = pattern_config.key_type_cls
                key = key_type.parse_obj(big_map.key)

                if action == BigMapAction.REMOVE:
                    value = None
                else:
                    value_type = pattern_config.value_type_cls
                    value = value_type.parse_obj(big_map.value)

                big_map_context = BigMapContext(  # type: ignore
                    action=action,
                    key=key,
                    value=value,
                )

                big_map_contexts.append(big_map_context)

            args.append(big_map_contexts)

        await handler_config.callback_fn(*args)

    @classmethod
    def convert_operation(cls, operation_json: Dict[str, Any]) -> OperationData:
        storage = operation_json.get('storage')
        # FIXME: KT1CpeSQKdkhWi4pinYcseCFKmDhs5M74BkU
        if not isinstance(storage, Dict):
            storage = {}

        return OperationData(
            # FIXME: type is null
            type=operation_json['type'] or 'transaction',
            id=operation_json['id'],
            level=operation_json['level'],
            timestamp=operation_json['timestamp'],
            block=operation_json.get('block'),
            hash=operation_json['hash'],
            counter=operation_json['counter'],
            sender_address=operation_json['sender']['address'],
            target_address=operation_json['target']['address'],
            amount=operation_json['amount'],
            status=operation_json['status'],
            has_internals=operation_json['hasInternals'],
            sender_alias=operation_json['sender'].get('alias'),
            nonce=operation_json.get('nonce'),
            target_alias=operation_json['target'].get('alias'),
            entrypoint=operation_json['parameter']['entrypoint'] if operation_json.get('parameter') else None,
            parameter_json=operation_json['parameter']['value'] if operation_json.get('parameter') else None,
            initiator_address=operation_json['initiator']['address'] if operation_json.get('initiator') else None,
            parameter=operation_json.get('parameters'),
            storage=storage,
            diffs=operation_json.get('diffs'),
        )

    @classmethod
    def convert_big_map(cls, big_map_json: Dict[str, Any]) -> BigMapData:
        return BigMapData(
            id=big_map_json['id'],
            level=big_map_json['level'],
            # FIXME: operation_id field in API
            operation_id=big_map_json['level'],
            timestamp=big_map_json['timestamp'],
            bigmap=big_map_json['bigmap'],
            contract_address=big_map_json['contract']['address'],
            path=big_map_json['path'],
            action=big_map_json['action'],
            key=big_map_json.get('content', {}).get('key'),
            value=big_map_json.get('content', {}).get('value'),
        )

    async def get_latest_block(self) -> Dict[str, Any]:
        self._logger.info('Fetching latest block')
        block = await self._proxy.http_request(
            'get',
            url=f'{self._url}/v1/head',
            skip_cache=True,
        )
        self._logger.debug(block)
        return block
