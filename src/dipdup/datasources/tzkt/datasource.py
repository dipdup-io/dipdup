import asyncio
import logging
from collections import deque, namedtuple
from copy import copy
from enum import Enum
from typing import Any, AsyncGenerator, Awaitable, Callable, Deque, Dict, List, Optional, Set, Tuple, Union, cast

from aiosignalrcore.hub.base_hub_connection import BaseHubConnection  # type: ignore
from aiosignalrcore.hub_connection_builder import HubConnectionBuilder  # type: ignore
from aiosignalrcore.messages.completion_message import CompletionMessage  # type: ignore
from aiosignalrcore.transport.websockets.connection import ConnectionState  # type: ignore
from pydantic.dataclasses import dataclass
from tortoise.transactions import in_transaction

from dipdup.config import (
    ROLLBACK_HANDLER,
    BigMapHandlerConfig,
    BigMapHandlerPatternConfig,
    BigMapIndexConfig,
    ContractConfig,
    IndexConfigTemplateT,
    OperationHandlerConfig,
    OperationHandlerOriginationPatternConfig,
    OperationHandlerPatternConfigT,
    OperationHandlerTransactionPatternConfig,
    OperationIndexConfig,
)
from dipdup.datasources.proxy import DatasourceRequestProxy
from dipdup.datasources.tzkt.enums import TzktMessageType
from dipdup.models import (
    BigMapAction,
    BigMapContext,
    BigMapData,
    OperationData,
    OriginationContext,
    State,
    TransactionContext,
)

OperationGroup = namedtuple('OperationGroup', ('hash', 'counter'))
OperationID = int

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


def dedup_operations(operations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        list(({op['id']: op for op in operations}).values()),
        key=lambda op: op['id'],
    )


class TzktRequestMixin:
    _logger: logging.Logger
    _url: str
    _proxy: DatasourceRequestProxy

    async def get_similar_contracts(self, address: Address, strict: bool = False) -> List[Address]:
        entrypoint = 'same' if strict else 'similar'
        self._logger.info('Fetching %s contracts for address `%s', entrypoint, address)

        contracts = await self._proxy.http_request(
            'get',
            url=f'{self._url}/v1/contracts/{address}/{entrypoint}',
            params=dict(
                select='address',
                limit=TZKT_HTTP_REQUEST_LIMIT,
            ),
        )
        return contracts

    async def get_originated_contracts(self, address: Address) -> List[Address]:
        contracts = await self._proxy.http_request(
            'get',
            url=f'{self._url}/v1/accounts/{address}/contracts',
            params=dict(
                limit=TZKT_HTTP_REQUEST_LIMIT,
            ),
            skip_cache=True,
        )
        return [c['address'] for c in contracts]

    async def get_contract_summary(self, address: Address) -> Dict[str, Any]:
        return await self._proxy.http_request('get', url=f'{self._url}/v1/contracts/{address}')

    async def get_contract_storage(self, address: Address) -> Dict[str, Any]:
        return await self._proxy.http_request('get', url=f'{self._url}/v1/contracts/{address}/storage')


class OperationFetcher(TzktRequestMixin):
    def __init__(
        self,
        url: str,
        proxy: DatasourceRequestProxy,
        first_level: int,
        last_level: int,
        transaction_subscriptions: Set[Address],
        origination_subscriptions: Set[OperationHandlerOriginationPatternConfig],
    ) -> None:
        self._url = url
        self._proxy = proxy
        self._first_level = first_level
        self._last_level = last_level
        self._transaction_subscriptions = transaction_subscriptions
        self._origination_subscriptions = origination_subscriptions
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
        if not self._origination_subscriptions:
            self._fetched[key] = True
            self._heads[key] = self._last_level
        if self._fetched[key]:
            return

        originated_contract_addresses: Set[str] = set()

        for pattern_config in self._origination_subscriptions:
            if pattern_config.originated_contract:
                originated_contract_addresses.add(pattern_config.originated_contract_config.address)
            if pattern_config.source:
                addresses = await self.get_originated_contracts(pattern_config.source_contract_config.address)
                for address in addresses:
                    originated_contract_addresses.add(address)
            if pattern_config.similar_to:
                addresses = await self.get_similar_contracts(pattern_config.similar_to_contract_config.address, pattern_config.strict)
                for address in addresses:
                    originated_contract_addresses.add(address)

        self._logger.debug('Fetching originations of %s', self._origination_subscriptions)

        originations = await self._proxy.http_request(
            'get',
            url=f'{self._url}/v1/operations/originations',
            params={
                "originatedContract.in": ','.join(originated_contract_addresses),
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

    async def _fetch_transactions(self, field: str) -> None:
        key = getattr(OperationFetcherChannel, field + '_transactions')
        if not self._transaction_subscriptions:
            self._fetched[key] = True
            self._heads[key] = self._last_level
        if self._fetched[key]:
            return

        self._logger.debug('Fetching %s transactions of %s', field, self._transaction_subscriptions)

        transactions = await self._proxy.http_request(
            'get',
            url=f'{self._url}/v1/operations/transactions',
            params={
                f"{field}.in": ','.join(self._transaction_subscriptions),
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

    async def fetch_operations_by_level(self) -> AsyncGenerator[Tuple[int, List[Dict[str, Any]]], None]:
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
                    yield self._head, dedup_operations(operations)
                self._head += 1

            if all(list(self._fetched.values())):
                break

        assert not self._operations


class OperationMatcher:
    def __init__(
        self,
        dipdup,
        indexes: Dict[str, OperationIndexConfig],
    ) -> None:
        self._logger = logging.getLogger(__name__)
        self._dipdup = dipdup
        self._indexes = indexes
        self._level: Optional[int] = None
        self._operations: Dict[OperationGroup, List[OperationData]] = {}

    async def add(self, operation: OperationData):
        self._logger.debug('Adding operation %s to cache (%s, %s)', operation.id, operation.hash, operation.counter)
        self._logger.debug('level=%s operation.level=%s', self._level, operation.level)

        if self._level is not None:
            if self._level != operation.level:
                raise RuntimeError('Operations must be splitted by level before caching')
        else:
            self._level = operation.level

        key = OperationGroup(operation.hash, operation.counter)
        if key not in self._operations:
            self._operations[key] = []
        self._operations[key].append(operation)

    def _match_operation(self, pattern_config: OperationHandlerPatternConfigT, operation: OperationData) -> bool:
        # NOTE: Reversed conditions are intentional
        if isinstance(pattern_config, OperationHandlerTransactionPatternConfig):
            if pattern_config.entrypoint != operation.entrypoint:
                return False
            if pattern_config.destination:
                if pattern_config.destination_contract_config.address != operation.target_address:
                    return False
            if pattern_config.source:
                if pattern_config.source_contract_config.address != operation.sender_address:
                    return False
            return True

        elif isinstance(pattern_config, OperationHandlerOriginationPatternConfig):
            if pattern_config.source:
                if pattern_config.source_contract_config.address != operation.sender_address:
                    return False
            if pattern_config.originated_contract:
                if pattern_config.originated_contract_config.address != operation.originated_contract_address:
                    return False
            if pattern_config.similar_to:
                if pattern_config.strict:
                    if pattern_config.similar_to_contract_config.code_hash != operation.originated_contract_code_hash:
                        return False
                else:
                    if pattern_config.similar_to_contract_config.type_hash != operation.originated_contract_type_hash:
                        return False
            return True
        else:
            raise NotImplementedError

    async def process(self) -> int:
        """Try to match operations in cache with all patterns from indexes."""
        if self._level is None:
            raise RuntimeError('Add operations to cache before processing')

        keys = list(self._operations.keys())
        self._logger.info('Matching %s operation groups', len(keys))
        for key, operations in self._operations.items():
            self._logger.debug('Matching %s', key)
            matched = False

            for index_config in self._indexes.values():
                if index_config.state.level > self._level:
                    continue
                for handler_config in index_config.handlers:
                    operation_idx = 0
                    pattern_idx = 0
                    matched_operations: List[Optional[OperationData]] = []

                    # TODO: Ensure complex cases work, for ex. required argument after optional one
                    # TODO: Add None to matched_operations where applicable
                    while operation_idx < len(operations):
                        pattern_config = handler_config.pattern[pattern_idx]
                        matched = self._match_operation(pattern_config, operations[operation_idx])
                        if matched:
                            matched_operations.append(operations[operation_idx])
                            pattern_idx += 1
                            operation_idx += 1
                        elif pattern_config.optional:
                            matched_operations.append(None)
                            pattern_idx += 1
                        else:
                            operation_idx += 1

                        if pattern_idx == len(handler_config.pattern):
                            self._logger.info('Handler `%s` matched! %s', handler_config.callback, key)
                            await self.on_match(index_config, handler_config, matched_operations, operations)
                            matched = True
                            matched_operations = []
                            pattern_idx = 0

                    if len(matched_operations) >= sum(map(lambda x: 0 if x.optional else 1, handler_config.pattern)):
                        self._logger.info('Handler `%s` matched! %s', handler_config.callback, key)
                        await self.on_match(index_config, handler_config, matched_operations, operations)
                        matched = True

                # NOTE: Only one index could match as addresses do not intersect between indexes (checked on config initialization)
                # TODO: Ensure it's really checked
                if matched:
                    break

        self._logger.info('Current level: %s', self._level)
        self._operations = {}

        level = self._level
        self._level = None
        return level

    async def on_match(
        self,
        index_config: OperationIndexConfig,
        handler_config: OperationHandlerConfig,
        matched_operations: List[Optional[OperationData]],
        operations: List[OperationData],
    ):
        """Prepare handler context and arguments, parse parameter and storage. Schedule callback in executor."""
        args: List[Optional[Union[TransactionContext, OriginationContext, OperationData]]] = []
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

        await self._dipdup.spawn_operation_handler_callback(index_config, handler_config, args, self._level, operations)


class BigMapMatcher:
    def __init__(self, dipdup: 'DipDup', indexes: Dict[str, BigMapIndexConfig]) -> None:
        super().__init__()
        self._logger = logging.getLogger(__name__)
        self._dipdup = dipdup
        self._indexes = indexes
        self._level: Optional[int] = None
        self._big_maps: Dict[OperationID, List[BigMapData]] = {}

    @property
    def level(self) -> Optional[int]:
        return self._level

    async def add(self, big_map: BigMapData):
        self._logger.debug('Adding big map %s to cache (%s)', big_map.id, big_map.operation_id)
        self._logger.debug('level=%s operation.level=%s', self._level, big_map.level)

        if self._level is not None:
            if self._level != big_map.level:
                raise RuntimeError('Big maps must be splitted by level before caching')
        else:
            self._level = big_map.level

        key = big_map.operation_id
        if key not in self._big_maps:
            self._big_maps[key] = []
        self._big_maps[key].append(big_map)

    def match_big_map(self, pattern_config: BigMapHandlerPatternConfig, big_map: BigMapData) -> bool:
        self._logger.debug('pattern: %s, %s', pattern_config.path, pattern_config.contract_config.address)
        self._logger.debug('big_map: %s, %s', big_map.path, big_map.contract_address)
        if pattern_config.path != big_map.path:
            return False
        if pattern_config.contract_config.address != big_map.contract_address:
            return False
        self._logger.debug('match!')
        return True

    async def process(self) -> int:
        if self._level is None:
            raise RuntimeError('Add big maps to cache before processing')

        keys = list(self._big_maps.keys())
        self._logger.info('Matching %s big map groups', len(keys))
        for key, big_maps in copy(self._big_maps).items():
            self._logger.debug('Processing %s', key)
            matched = False

            for index_config in self._indexes.values():
                if matched:
                    break
                for handler_config in index_config.handlers:
                    matched_big_maps: List[List[BigMapData]] = [[] for _ in range(len(handler_config.pattern))]
                    for i, pattern_config in enumerate(handler_config.pattern):
                        for big_map in big_maps:
                            big_map_matched = self.match_big_map(pattern_config, big_map)
                            if big_map_matched:
                                matched_big_maps[i].append(big_map)

                    if any([len(big_map_group) for big_map_group in matched_big_maps]):
                        self._logger.info('Handler `%s` matched! %s', handler_config.callback, key)
                        matched = True
                        await self._dipdup.spawn_big_map_handler_callback(index_config, handler_config, matched_big_maps, self._level)
                        del self._big_maps[key]
                        break

        keys_left = self._big_maps.keys()
        self._logger.info('%s operation groups unmatched', len(keys_left))
        self._logger.info('Current level: %s', self._level)
        self._big_maps = {}

        level = self._level
        self._level = None
        return level

    async def on_match(
        self,
        index_config: BigMapIndexConfig,
        handler_config: BigMapHandlerConfig,
        matched_big_maps: List[List[BigMapData]],
    ):
        args: List[List[BigMapContext]] = []
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

        await self._dipdup.spawn_big_map_handler_callback(index_config, handler_config, args, self._level)


class TzktDatasource(TzktRequestMixin):
    def __init__(self, url: str, dipdup: 'DipDup'):
        self._url = url.rstrip('/')
        self._logger = logging.getLogger(__name__)
        self._operation_indexes: Dict[IndexName, OperationIndexConfig] = {}
        self._big_map_indexes: Dict[IndexName, BigMapIndexConfig] = {}
        self._transaction_subscriptions: Set[Address] = set()
        self._origination_subscriptions: Set[OperationHandlerOriginationPatternConfig] = set()
        self._big_map_subscriptions: Dict[Address, List[Path]] = {}
        self._operations_synchronized = asyncio.Event()
        self._big_maps_synchronized = asyncio.Event()
        self._client: Optional[BaseHubConnection] = None

        self._operation_matcher = OperationMatcher(dipdup, self._operation_indexes)
        self._big_map_matcher = BigMapMatcher(dipdup, self._big_map_indexes)

        self._dipdup = dipdup
        self._proxy = DatasourceRequestProxy(self._dipdup._config.cache_enabled)
        self._synched_indexes: List[str] = []

    async def add_index(self, index_name: str, index_config: IndexConfigTemplateT) -> None:
        """Register index config in internal mappings and caches. Find and register subscriptions.
        If called in runtime need to `resync` then."""
        self._logger.info('Adding index `%s`', index_name)

        if isinstance(index_config, OperationIndexConfig):
            await index_config.fetch_hashes(self)
            self._operation_indexes[index_name] = index_config

            for contract_config in index_config.contracts or []:
                self._transaction_subscriptions.add(cast(ContractConfig, contract_config).address)

            for handler_config in index_config.handlers:
                for pattern_config in handler_config.pattern:
                    if isinstance(pattern_config, OperationHandlerOriginationPatternConfig):
                        self._origination_subscriptions.add(pattern_config)

        elif isinstance(index_config, BigMapIndexConfig):
            self._big_map_indexes[index_name] = index_config

            for big_map_handler_config in index_config.handlers:
                for big_map_pattern_config in big_map_handler_config.pattern:
                    address, path = big_map_pattern_config.contract_config.address, big_map_pattern_config.path
                    if address not in self._big_map_subscriptions:
                        self._big_map_subscriptions[address] = []
                    if path not in self._big_map_subscriptions[address]:
                        self._big_map_subscriptions[address].append(path)

        else:
            raise NotImplementedError(f'Index kind `{index_config.kind}` is not supported')

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

    async def set_state_level(self, index_config: IndexConfigTemplateT, level: int) -> None:
        index_config.state.level = level  # type: ignore
        await index_config.state.save()

    async def fetch_index(self, index_name: str, index_config: IndexConfigTemplateT, level: int) -> None:
        self._logger.info('Synchronizing `%s`', index_name)
        if isinstance(index_config, OperationIndexConfig):
            await self.fetch_operations(index_config, level)
        elif isinstance(index_config, BigMapIndexConfig):
            await self.fetch_big_maps(index_config, level)
        else:
            raise NotImplementedError

    async def run(self):
        """Sync indexes via REST, start WS connection"""
        self._logger.info('Starting datasource')
        rest_only = False

        latest_block = await self.get_latest_block()

        self._logger.info('Initial synchronizing operation indexes')
        for index_config_name, operation_index_config in self._operation_indexes.items():
            if operation_index_config.last_block:
                current_level = operation_index_config.last_block
                rest_only = True
            else:
                current_level = latest_block['level']

            await self.fetch_index(index_config_name, operation_index_config, current_level)

        self._logger.info('Initial synchronizing big map indexes')
        for index_config_name, big_map_index_config in self._big_map_indexes.items():
            if big_map_index_config.last_block:
                current_level = big_map_index_config.last_block
                rest_only = True
            else:
                current_level = latest_block['level']

            await self.fetch_index(index_config_name, big_map_index_config, current_level)

        # while self._dipdup._executor._queue:
        #     await asyncio.sleep(0.1)

        if not rest_only:
            self._logger.info('Starting websocket client')
            await self._get_client().start()

    async def stop(self):
        ...

    async def on_connect(self):
        self._logger.info('Connected to server')
        for address in self._transaction_subscriptions:
            await self.subscribe_to_transactions(address)
        # NOTE: All originations are passed to matcher
        if self._origination_subscriptions:
            await self.subscribe_to_originations()
        for address, paths in self._big_map_subscriptions.items():
            await self.subscribe_to_big_maps(address, paths)

    def on_error(self, message: CompletionMessage):
        raise Exception(message.error)

    async def subscribe_to_transactions(self, address: str) -> None:
        self._logger.info('Subscribing to %s transactions', address)

        while self._get_client().transport.state != ConnectionState.connected:
            await asyncio.sleep(0.1)

        await self._get_client().send(
            'SubscribeToOperations',
            [
                {
                    'address': address,
                    'types': 'transaction',
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

    async def fetch_operations(self, index_config: OperationIndexConfig, last_level: int) -> None:
        if isinstance(index_config.state, State):
            first_level = index_config.state.level
            if first_level == last_level:
                return
        else:
            first_level = 0

        self._logger.info('Fetching operations from level %s to %s', first_level, last_level)

        fetcher = OperationFetcher(
            url=self._url,
            proxy=self._proxy,
            first_level=first_level,
            last_level=last_level,
            transaction_subscriptions=self._transaction_subscriptions,
            origination_subscriptions=self._origination_subscriptions,
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

        # NOTE: State level is not updated when there's no operations between first_level and last_level
        await self.set_state_level(index_config, last_level)

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

        if isinstance(index_config.state, State):
            first_level = index_config.state.level
            if first_level == last_level:
                return
        else:
            first_level = 0

        self._logger.info('Fetching big map updates from level %s to %s', first_level, last_level)

        big_maps = []
        offset = 0
        addresses, paths = set(), set()
        for handler_config in index_config.handlers:
            for pattern_config in handler_config.pattern:
                addresses.add(pattern_config.contract_config.address)
                paths.add(pattern_config.path)

        while True:
            fetched_big_maps = await self._fetch_big_maps(list(addresses), list(paths), offset, first_level, last_level)
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

        # NOTE: State level is not updated when there's no operations between first_level and last_level
        await self.set_state_level(index_config, last_level)

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
                for index_config in self._operation_indexes.values():
                    first_level = index_config.state.level
                    self._logger.info('Got state message, current level %s, index level %s', last_level, first_level)
                    await self.fetch_operations(index_config, last_level)
                self._operations_synchronized.set()

            elif message_type == TzktMessageType.DATA:
                if not sync and not self._operations_synchronized.is_set():
                    self._logger.info('Waiting until synchronization is complete')
                    await self._operations_synchronized.wait()
                    self._logger.info('Synchronization is complete, processing websocket message')

                for operation_json in item['data']:
                    operation = self.convert_operation(operation_json)
                    if operation.status != 'applied':
                        continue

                    await self._operation_matcher.add(operation)

                await self._operation_matcher.process()

            elif message_type == TzktMessageType.REORG:
                self._logger.info('Got reorg message, calling `%s` handler', ROLLBACK_HANDLER)
                # NOTE: It doesn't matter which index to get
                from_level = list(self._operation_indexes.values())[0].state.level
                to_level = item['state']
                await self._dipdup.spawn_rollback_handler_callback(from_level, to_level)

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
                for index_config in self._big_map_indexes.values():
                    self._logger.info('Got state message, current level %s', last_level)
                    await self.fetch_big_maps(index_config, last_level)
                self._big_maps_synchronized.set()

            elif message_type == TzktMessageType.DATA:
                if not sync and not self._big_maps_synchronized.is_set():
                    self._logger.info('Waiting until synchronization is complete')
                    await self._big_maps_synchronized.wait()
                    self._logger.info('Synchronization is complete, processing websocket message')

                self._logger.info('Acquiring callback lock')

                for big_map_json in item['data']:
                    big_map = self.convert_big_map(big_map_json)
                    await self._big_map_matcher.add(big_map)

                await self._big_map_matcher.process()

            elif message_type == TzktMessageType.REORG:
                self._logger.info('Got reorg message, calling `%s` handler', ROLLBACK_HANDLER)
                # NOTE: It doesn't matter which index to get
                from_level = list(self._big_map_indexes.values())[0].state.level
                to_level = item['state']
                await self._dipdup.spawn_rollback_handler_callback(from_level, to_level)

            else:
                self._logger.warning('%s is not supported', message_type)

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

    async def resync(self) -> None:
        self._operations_synchronized.clear()
        self._big_maps_synchronized.clear()
        await self.on_connect()
