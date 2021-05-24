import asyncio
import logging
from collections import deque
from enum import Enum
from typing import Any, Awaitable, Callable, Deque, Dict, List, Optional, Union, cast

from aiosignalrcore.hub.base_hub_connection import BaseHubConnection  # type: ignore
from aiosignalrcore.hub_connection_builder import HubConnectionBuilder  # type: ignore
from aiosignalrcore.messages.completion_message import CompletionMessage  # type: ignore
from aiosignalrcore.transport.websockets.connection import ConnectionState  # type: ignore
from pydantic.dataclasses import dataclass
from tortoise.transactions import in_transaction

from dipdup import __version__
from dipdup.config import (
    ROLLBACK_HANDLER,
    BigMapHandlerConfig,
    BigMapIndexConfig,
    BlockIndexConfig,
    ContractConfig,
    DipDupConfig,
    IndexConfigTemplateT,
    OperationHandlerConfig,
    OperationHandlerOriginationPatternConfig,
    OperationHandlerTransactionPatternConfig,
    OperationIndexConfig,
    OperationType,
    StaticTemplateConfig,
    TzktDatasourceConfig,
)
from dipdup.datasources.tzkt.cache import BigMapCache, OperationCache
from dipdup.datasources.tzkt.enums import TzktMessageType
from dipdup.datasources.tzkt.proxy import TzktRequestProxy
from dipdup.models import (
    BigMapAction,
    BigMapContext,
    BigMapData,
    BigMapHandlerContext,
    OperationData,
    OperationHandlerContext,
    OriginationContext,
    TransactionContext,
)

TZKT_HTTP_REQUEST_LIMIT = 10000
OPERATION_FIELDS = (
    "type",
    "id",
    "level",
    "timestamp",
    "hash",
    "counter",
    "sender",
    "nonce",
    "target",
    "amount",
    "storage",
    "status",
    "hasInternals",
    "diffs",
)
ORIGINATION_OPERATION_FIELDS = (
    *OPERATION_FIELDS,
    "originatedContract",
)
TRANSACTION_OPERATION_FIELDS = (
    *OPERATION_FIELDS,
    "parameter",
    "hasInternals",
)


IndexName = str
Address = str
Path = str


@dataclass
class ContractSubscription:
    type_hash: str
    code_hash: str
    strict: bool
    template: IndexConfigTemplateT
    template_name: str
    contract_config: ContractConfig


class OperationFetcherChannel(Enum):
    sender_transactions = 'sender_transactions'
    target_transactions = 'target_transactions'
    originations = 'originations'


class CallbackExecutor:
    def __init__(self) -> None:
        self._queue: Deque[Awaitable] = deque()

    def submit(self, fn, *args, **kwargs):
        self._queue.append(fn(*args, **kwargs))

    async def run(self):
        while True:
            try:
                coro = self._queue.popleft()
                await coro
            except IndexError:
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                return


class OperationFetcher:
    def __init__(
        self,
        url: str,
        proxy: TzktRequestProxy,
        first_level: int,
        last_level: int,
        addresses: List[str],
        operation_subscriptions: Dict[Address, List[OperationType]],
    ) -> None:
        self._url = url
        self._proxy = proxy
        self._first_level = first_level
        self._last_level = last_level
        self._origination_addresses = [
            address for address, types in operation_subscriptions.items() if address in addresses and OperationType.origination in types
        ]
        self._transaction_addresses = [
            address for address, types in operation_subscriptions.items() if address in addresses and OperationType.transaction in types
        ]
        self._logger = logging.getLogger(__name__)
        self._head: int = 0
        self._heads: Dict[OperationFetcherChannel, int] = {}
        self._offsets: Dict[OperationFetcherChannel, int] = {}
        self._fetched: Dict[OperationFetcherChannel, bool] = {}
        self._operations: Dict[int, List[Dict[str, Any]]] = {}

    def _get_head(self, operations: List[Dict[str, Any]]):
        for i in range(len(operations) - 1)[::-1]:
            if operations[i]['level'] != operations[i + 1]['level']:
                return operations[i]['level']
        return operations[0]['level']

    async def _fetch_originations(self) -> None:
        key = OperationFetcherChannel.originations
        if not self._origination_addresses:
            self._fetched[key] = True
            self._heads[key] = self._last_level
        if self._fetched[key]:
            return

        self._logger.debug('Fetching originations of %s', self._origination_addresses)

        originations = await self._proxy.http_request(
            'get',
            url=f'{self._url}/v1/operations/originations',
            params={
                "originatedContract.in": ','.join(self._origination_addresses),
                "offset": self._offsets[key],
                "limit": TZKT_HTTP_REQUEST_LIMIT,
                "level.gt": self._first_level,
                "level.le": self._last_level,
                "select": ','.join(ORIGINATION_OPERATION_FIELDS),
                "status": "applied",
            },
        )

        for op in originations:
            # NOTE: type needs to be set manually when requesting operations by specific type
            op['type'] = 'origination'
            level = op['level']
            if level not in self._operations:
                self._operations[level] = []
            self._operations[level].append(op)

        self._logger.debug('Got %s', len(originations))

        if len(originations) < TZKT_HTTP_REQUEST_LIMIT:
            self._fetched[key] = True
            self._heads[key] = self._last_level
        else:
            self._offsets[key] += TZKT_HTTP_REQUEST_LIMIT
            self._heads[key] = self._get_head(originations)

    async def _fetch_transactions(self, field: str):
        key = getattr(OperationFetcherChannel, field + '_transactions')
        if not self._transaction_addresses:
            self._fetched[key] = True
            self._heads[key] = self._last_level
        if self._fetched[key]:
            return

        self._logger.debug('Fetching %s transactions of %s', field, self._transaction_addresses)

        transactions = await self._proxy.http_request(
            'get',
            url=f'{self._url}/v1/operations/transactions',
            params={
                f"{field}.in": ','.join(self._transaction_addresses),
                "offset": self._offsets[key],
                "limit": TZKT_HTTP_REQUEST_LIMIT,
                "level.gt": self._first_level,
                "level.le": self._last_level,
                "select": ','.join(TRANSACTION_OPERATION_FIELDS),
                "status": "applied",
            },
        )

        for op in transactions:
            # NOTE: type needs to be set manually when requesting operations by specific type
            op['type'] = 'transaction'
            level = op['level']
            if level not in self._operations:
                self._operations[level] = []
            self._operations[level].append(op)

        self._logger.debug('Got %s', len(transactions))

        if len(transactions) < TZKT_HTTP_REQUEST_LIMIT:
            self._fetched[key] = True
            self._heads[key] = self._last_level
        else:
            self._offsets[key] += TZKT_HTTP_REQUEST_LIMIT
            self._heads[key] = self._get_head(transactions)

    async def fetch_operations_by_level(self):
        for type_ in (
            OperationFetcherChannel.sender_transactions,
            OperationFetcherChannel.target_transactions,
            OperationFetcherChannel.originations,
        ):
            self._heads[type_] = 0
            self._offsets[type_] = 0
            self._fetched[type_] = False

        while True:
            min_head = sorted(self._heads.items(), key=lambda x: x[1])[0][0]
            if min_head == OperationFetcherChannel.originations:
                await self._fetch_originations()
            elif min_head == OperationFetcherChannel.target_transactions:
                await self._fetch_transactions('target')
            elif min_head == OperationFetcherChannel.sender_transactions:
                await self._fetch_transactions('sender')
            else:
                raise RuntimeError

            head = min(self._heads.values())
            while self._head <= head:
                if self._head in self._operations:
                    operations = self._operations.pop(self._head)
                    operations = sorted(list(({op['id']: op for op in operations}).values()), key=lambda op: op['id'])
                    yield self._head, operations
                self._head += 1

            if all(list(self._fetched.values())):
                break

        assert not self._operations


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
        self._contract_subscriptions: List[ContractSubscription] = []
        self._big_map_subscriptions: Dict[Address, List[Path]] = {}
        self._operations_synchronized = asyncio.Event()
        self._big_maps_synchronized = asyncio.Event()
        self._client: Optional[BaseHubConnection] = None
        self._operation_cache = OperationCache()
        self._big_map_cache = BigMapCache()
        self._rollback_fn: Optional[Callable[[int, int], Awaitable[None]]] = None
        self._package: Optional[str] = None
        self._proxy = TzktRequestProxy(cache)
        self._callback_executor = CallbackExecutor()

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

    def set_package(self, package: str) -> None:
        self._package = package

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

            async def operation_callback(*args, **kwargs) -> None:
                self._callback_executor.submit(self.on_operation_message, *args, **kwargs)

            async def big_map_callback(*args, **kwargs) -> None:
                self._callback_executor.submit(self.on_big_map_message, *args, **kwargs)

            self._client.on_open(self.on_connect)
            self._client.on_error(self.on_error)
            self._client.on('operations', operation_callback)
            self._client.on('bigmaps', big_map_callback)

        return self._client

    async def start(self):
        self._logger.info('Starting datasource')
        rest_only = False

        for operation_index_config in self._operation_index_by_name.values():
            for contract in operation_index_config.contracts:
                await self.add_operation_subscription(contract.address, operation_index_config.types)

        for big_map_index_config in self._big_map_index_by_name.values():
            for handler_config in big_map_index_config.handlers:
                for pattern_config in handler_config.pattern:
                    await self.add_big_map_subscription(pattern_config.contract_config.address, pattern_config.path)

        latest_block = await self.get_latest_block()

        self._logger.info('Initial synchronizing operation indexes')
        for index_config_name, operation_index_config in self._operation_index_by_name.items():
            self._logger.info('Synchronizing `%s`', index_config_name)
            if operation_index_config.last_block:
                current_level = operation_index_config.last_block
                rest_only = True
            else:
                current_level = latest_block['level']

            await self.fetch_operations(operation_index_config, current_level)

        self._logger.info('Initial synchronizing big map indexes')
        for index_config_name, big_map_index_config in self._big_map_index_by_name.items():
            self._logger.info('Synchronizing `%s`', index_config_name)
            if big_map_index_config.last_block:
                current_level = big_map_index_config.last_block
                rest_only = True
            else:
                current_level = latest_block['level']

            await self.fetch_big_maps(big_map_index_config, current_level)

        if not rest_only:
            self._logger.info('Starting websocket client')
            await asyncio.gather(
                await self._get_client().start(),
                await self._callback_executor.run(),
            )

    async def stop(self):
        ...

    async def on_connect(self):
        self._logger.info('Connected to server')
        for address, types in self._operation_subscriptions.items():
            await self.subscribe_to_operations(address, types)
        for address, paths in self._big_map_subscriptions.items():
            await self.subscribe_to_big_maps(address, paths)
        if self._contract_subscriptions:
            await self.subscribe_to_originations()

    def on_error(self, message: CompletionMessage):
        raise Exception(message.error)

    async def subscribe_to_operations(self, address: str, types: List[OperationType]) -> None:
        self._logger.info('Subscribing to %s, %s', address, types)

        while self._get_client().transport.state != ConnectionState.connected:
            await asyncio.sleep(0.1)

        await self._get_client().send(
            'SubscribeToOperations',
            [
                {
                    'address': address,
                    'types': ','.join([t.value for t in types]),
                }
            ],
        )

    async def subscribe_to_originations(self) -> None:
        self._logger.info('Subscribing to originations')

        while self._get_client().transport.state != ConnectionState.connected:
            await asyncio.sleep(0.1)

        await self._get_client().send(
            'SubscribeToOperations',
            [
                {
                    'types': 'origination',
                }
            ],
        )

    async def subscribe_to_big_maps(self, address: Address, paths: List[Path]) -> None:
        self._logger.info('Subscribing to big map updates of %s, %s', address, paths)

        while self._get_client().transport.state != ConnectionState.connected:
            await asyncio.sleep(0.1)

        for path in paths:
            await self._get_client().send(
                'SubscribeToBigMaps',
                [
                    {
                        'address': address,
                        'path': path,
                    }
                ],
            )

    async def add_contract_subscription(
        self,
        contract_config: ContractConfig,
        template_name: str,
        template: IndexConfigTemplateT,
        strict: bool,
    ) -> None:
        contract = await self._proxy.http_request(
            'get',
            url=f'{self._url}/v1/contracts/{contract_config.address}',
            params={
                "select": "typeHash,codeHash",
            },
        )
        self._contract_subscriptions.append(
            ContractSubscription(
                type_hash=contract['typeHash'],
                code_hash=contract['codeHash'],
                strict=strict,
                template=template,
                template_name=template_name,
                contract_config=contract_config,
            )
        )

    async def fetch_operations(self, index_config: OperationIndexConfig, last_level: int) -> None:
        self._logger.info('Fetching operations prior to level %s', last_level)

        first_level = index_config.state.level
        addresses = [c.address for c in index_config.contract_configs]

        fetcher = OperationFetcher(
            url=self._url,
            proxy=self._proxy,
            first_level=first_level,
            last_level=last_level,
            addresses=addresses,
            operation_subscriptions=self._operation_subscriptions,
        )

        async for level, operations in fetcher.fetch_operations_by_level():
            self._logger.info('Processing %s operations of level %s', len(operations), level)
            await self.on_operation_message(
                message=[
                    {
                        'type': TzktMessageType.DATA.value,
                        'data': operations,
                    },
                ],
                sync=True,
            )

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

    async def fetch_big_maps(self, index_config: BigMapIndexConfig, last_level: int) -> None:
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

        if big_maps:
            await _process_level_big_maps(big_maps)

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
                last_level = item['state']
                for index_config in self._operation_index_by_name.values():
                    first_level = index_config.state.level
                    self._logger.info('Got state message, current level %s, index level %s', last_level, first_level)
                    await self.fetch_operations(index_config, last_level)
                self._operations_synchronized.set()

            elif message_type == TzktMessageType.DATA:
                if not sync and not self._operations_synchronized.is_set():
                    self._logger.info('Waiting until synchronization is complete')
                    await self._operations_synchronized.wait()
                    self._logger.info('Synchronization is complete, processing websocket message')

                self._logger.info('Acquiring callback lock')
                async with self._callback_lock:
                    for operation_json in item['data']:
                        operation = self.convert_operation(operation_json)
                        if operation.status != 'applied':
                            continue

                        if operation.originated_contract_address:
                            for contract_subscription in self._contract_subscriptions:
                                if (
                                    contract_subscription.strict is True
                                    and contract_subscription.code_hash == operation.originated_contract_code_hash
                                ):
                                    await self.on_contract_match(contract_subscription, operation.originated_contract_address)
                                if (
                                    contract_subscription.strict is False
                                    and contract_subscription.type_hash == operation.originated_contract_type_hash
                                ):
                                    await self.on_contract_match(contract_subscription, operation.originated_contract_address)

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
                last_level = item['state']
                for index_config in self._big_map_index_by_name.values():
                    first_level = self._operation_cache.level
                    self._logger.info('Got state message, current level %s, index level %s', first_level, first_level)
                    await self.fetch_big_maps(index_config, last_level)
                self._big_maps_synchronized.set()

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

    async def add_operation_subscription(self, address: str, types: Optional[List[OperationType]] = None) -> None:
        if types is None:
            types = [OperationType.transaction]
        if address not in self._operation_subscriptions:
            self._operation_subscriptions[address] = types

    async def add_big_map_subscription(self, address: str, path: str) -> None:
        if address not in self._big_map_subscriptions:
            self._big_map_subscriptions[address] = []
        self._big_map_subscriptions[address].append(path)

    async def on_operation_match(
        self,
        index_config: OperationIndexConfig,
        handler_config: OperationHandlerConfig,
        matched_operations: List[Optional[OperationData]],
        operations: List[OperationData],
    ):
        handler_context = OperationHandlerContext(
            operations=operations,
            template_values=index_config.template_values,
        )
        args: List[Optional[Union[OperationHandlerContext, TransactionContext, OriginationContext, OperationData]]] = [handler_context]
        for pattern_config, operation in zip(handler_config.pattern, matched_operations):
            if operation is None:
                args.append(None)

            elif isinstance(pattern_config, OperationHandlerTransactionPatternConfig):
                if not pattern_config.entrypoint:
                    args.append(operation)
                    continue

                parameter_type = pattern_config.parameter_type_cls
                parameter = parameter_type.parse_obj(operation.parameter_json) if parameter_type else None

                storage_type = pattern_config.storage_type_cls
                storage = operation.get_merged_storage(storage_type)

                transaction_context = TransactionContext(
                    data=operation,
                    parameter=parameter,
                    storage=storage,
                )
                args.append(transaction_context)

            elif isinstance(pattern_config, OperationHandlerOriginationPatternConfig):
                storage_type = pattern_config.storage_type_cls
                storage = operation.get_merged_storage(storage_type)

                origination_context = OriginationContext(
                    data=operation,
                    storage=storage,
                )
                args.append(origination_context)

            else:
                raise NotImplementedError

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

    async def on_contract_match(self, contract_subscription: ContractSubscription, address: Address) -> None:
        # FIXME: Summons tainted souls into the realm of the living
        datasource_name = cast(str, contract_subscription.template.datasource)
        temp_config = DipDupConfig(
            spec_version='0.1',
            package=cast(str, self._package),
            contracts=dict(contract=contract_subscription.contract_config),
            datasources={datasource_name: TzktDatasourceConfig(kind='tzkt', url=self._url)},
            indexes={
                f'{contract_subscription.template_name}_{address}': StaticTemplateConfig(
                    template='template',
                    values=dict(
                        contract='contract',
                    ),
                )
            },
            templates=dict(template=contract_subscription.template),
        )
        temp_config.pre_initialize()
        await temp_config.initialize()
        index_name, index_config = list(temp_config.indexes.items())[0]
        await self.add_index(index_name, cast(IndexConfigTemplateT, index_config))
        await self.on_connect()

    @classmethod
    def convert_operation(cls, operation_json: Dict[str, Any]) -> OperationData:
        storage = operation_json.get('storage')
        # FIXME: Plain storage, has issues in codegen: KT1CpeSQKdkhWi4pinYcseCFKmDhs5M74BkU
        if not isinstance(storage, Dict):
            storage = {}

        return OperationData(
            type=operation_json['type'],
            id=operation_json['id'],
            level=operation_json['level'],
            timestamp=operation_json['timestamp'],
            block=operation_json.get('block'),
            hash=operation_json['hash'],
            counter=operation_json['counter'],
            sender_address=operation_json['sender']['address'] if operation_json.get('sender') else None,
            target_address=operation_json['target']['address'] if operation_json.get('target') else None,
            amount=operation_json['amount'],
            status=operation_json['status'],
            has_internals=operation_json['hasInternals'],
            sender_alias=operation_json['sender'].get('alias'),
            nonce=operation_json.get('nonce'),
            target_alias=operation_json['target'].get('alias') if operation_json.get('target') else None,
            entrypoint=operation_json['parameter']['entrypoint'] if operation_json.get('parameter') else None,
            parameter_json=operation_json['parameter']['value'] if operation_json.get('parameter') else None,
            originated_contract_address=operation_json['originatedContract']['address']
            if operation_json.get('originatedContract')
            else None,
            originated_contract_type_hash=operation_json['originatedContract']['typeHash']
            if operation_json.get('originatedContract')
            else None,
            originated_contract_code_hash=operation_json['originatedContract']['codeHash']
            if operation_json.get('originatedContract')
            else None,
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

    async def get_similar_contracts(self, address: Address, strict: bool = False) -> List[Address]:
        entrypoint = 'same' if strict else 'similar'
        self._logger.info('Fetching %s contracts for address `%s', entrypoint, address)

        contracts = await self._proxy.http_request(
            'get',
            url=f'{self._url}/v1/contracts/{address}/{entrypoint}?select=address',
            params=dict(
                select='address',
                limit=TZKT_HTTP_REQUEST_LIMIT,
            ),
        )
        return contracts
