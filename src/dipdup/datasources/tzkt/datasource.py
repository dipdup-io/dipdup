import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, AsyncGenerator, DefaultDict, Dict, List, NoReturn, Optional, Set, Tuple, cast

from aiohttp import ClientResponseError
from aiosignalrcore.hub.base_hub_connection import BaseHubConnection  # type: ignore
from aiosignalrcore.hub_connection_builder import HubConnectionBuilder  # type: ignore
from aiosignalrcore.messages.completion_message import CompletionMessage  # type: ignore
from aiosignalrcore.transport.websockets.connection import ConnectionState  # type: ignore

from dipdup.config import (
    BigMapIndexConfig,
    ContractConfig,
    HTTPConfig,
    IndexConfigTemplateT,
    OperationHandlerOriginationPatternConfig,
    OperationIndexConfig,
)
from dipdup.datasources.datasource import IndexDatasource
from dipdup.datasources.tzkt.enums import TzktMessageType
from dipdup.models import BigMapAction, BigMapData, BlockData, HeadBlockData, OperationData
from dipdup.utils import groupby, split_by_chunks

OperationID = int

TZKT_ORIGINATIONS_REQUEST_LIMIT = 100
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
    "initiator",
    "amount",
    "storage",
    "status",
    "hasInternals",
    "diffs",
)
ORIGINATION_MIGRATION_FIELDS = (
    "id",
    "level",
    "timestamp",
    "storage",
    "diffs",
    "account",
    "balanceChange",
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


class OperationFetcherChannel(Enum):
    """Represents multiple TzKT calls to be merged into a single batch of operations"""

    sender_transactions = 'sender_transactions'
    target_transactions = 'target_transactions'
    originations = 'originations'


def dedup_operations(operations: List[OperationData]) -> List[OperationData]:
    """Merge operations from multiple endpoints"""
    return sorted(
        list(({op.id: op for op in operations}).values()),
        key=lambda op: op.id,
    )


class OperationFetcher:
    """Fetches and merges history of operations from multiple requests (channels) tracking their states independently.
    Created for each index while synchronizing via REST.
    """

    def __init__(
        self,
        datasource: 'TzktDatasource',
        first_level: int,
        last_level: int,
        transaction_addresses: Set[str],
        origination_addresses: Set[str],
        cache: bool = False,
        migration_originations: List[OperationData] = None,
    ) -> None:
        self._datasource = datasource
        self._first_level = first_level
        self._last_level = last_level
        self._transaction_addresses = transaction_addresses
        self._origination_addresses = origination_addresses
        self._cache = cache

        self._logger = logging.getLogger('dipdup.tzkt')
        self._head: int = 0
        self._heads: Dict[OperationFetcherChannel, int] = {}
        self._offsets: Dict[OperationFetcherChannel, int] = {}
        self._fetched: Dict[OperationFetcherChannel, bool] = {}

        self._operations: DefaultDict[int, List[OperationData]]
        if migration_originations:
            self._operations = groupby(migration_originations, lambda op: op.level)
        else:
            self._operations = defaultdict(list)

    def _get_operations_head(self, operations: List[OperationData]) -> int:
        """Get latest block level (head) of sorted operations batch"""
        for i in range(len(operations) - 1)[::-1]:
            if operations[i].level != operations[i + 1].level:
                return operations[i].level
        return operations[0].level

    async def _fetch_originations(self) -> None:
        """Fetch a single batch of originations, bump channel offset"""
        key = OperationFetcherChannel.originations
        if not self._origination_addresses:
            self._fetched[key] = True
            self._heads[key] = self._last_level
        if self._fetched[key]:
            return

        self._logger.debug('Fetching originations of %s', self._origination_addresses)

        originations = await self._datasource.get_originations(
            addresses=self._origination_addresses,
            offset=self._offsets[key],
            first_level=self._first_level,
            last_level=self._last_level,
            cache=self._cache,
        )

        for op in originations:
            level = op.level
            if level not in self._operations:
                self._operations[level] = []
            self._operations[level].append(op)

        self._logger.debug('Got %s', len(originations))

        if len(originations) < self._datasource.request_limit:
            self._fetched[key] = True
            self._heads[key] = self._last_level
        else:
            self._offsets[key] += self._datasource.request_limit
            self._heads[key] = self._get_operations_head(originations)

    async def _fetch_transactions(self, field: str) -> None:
        """Fetch a single batch of transactions, bump channel offset"""
        key = getattr(OperationFetcherChannel, field + '_transactions')
        if not self._transaction_addresses:
            self._fetched[key] = True
            self._heads[key] = self._last_level
        if self._fetched[key]:
            return

        self._logger.debug('Fetching %s transactions of %s', field, self._transaction_addresses)

        transactions = await self._datasource.get_transactions(
            field=field,
            addresses=self._transaction_addresses,
            offset=self._offsets[key],
            first_level=self._first_level,
            last_level=self._last_level,
            cache=self._cache,
        )

        for op in transactions:
            level = op.level
            if level not in self._operations:
                self._operations[level] = []
            self._operations[level].append(op)

        self._logger.debug('Got %s', len(transactions))

        if len(transactions) < self._datasource.request_limit:
            self._fetched[key] = True
            self._heads[key] = self._last_level
        else:
            self._offsets[key] += self._datasource.request_limit
            self._heads[key] = self._get_operations_head(transactions)

    async def fetch_operations_by_level(self) -> AsyncGenerator[Tuple[int, List[OperationData]], None]:
        """Iterate by operations from multiple channels. Return is splitted by level, deduped/sorted and ready to be passeed to Matcher."""
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


class BigMapFetcher:
    def __init__(
        self,
        datasource: 'TzktDatasource',
        first_level: int,
        last_level: int,
        big_map_addresses: Set[str],
        big_map_paths: Set[str],
        cache: bool = False,
    ) -> None:
        self._logger = logging.getLogger('dipdup.tzkt')
        self._datasource = datasource
        self._first_level = first_level
        self._last_level = last_level
        self._big_map_addresses = big_map_addresses
        self._big_map_paths = big_map_paths
        self._cache = cache

    async def fetch_big_maps_by_level(self) -> AsyncGenerator[Tuple[int, List[BigMapData]], None]:
        """Fetch big map diffs via Fetcher (not implemented yet) and pass to message callback"""

        offset = 0
        big_maps = []

        while True:
            fetched_big_maps = await self._datasource.get_big_maps(
                self._big_map_addresses,
                self._big_map_paths,
                offset,
                self._first_level,
                self._last_level,
                cache=self._cache,
            )
            big_maps += fetched_big_maps

            while True:
                for i in range(len(big_maps) - 1):
                    if big_maps[i].level != big_maps[i + 1].level:
                        yield big_maps[i].level, big_maps[: i + 1]
                        big_maps = big_maps[i + 1 :]  # noqa: E203
                        break
                else:
                    break

            if len(fetched_big_maps) < self._datasource.request_limit:
                break

            offset += self._datasource.request_limit

        if big_maps:
            yield big_maps[0].level, big_maps[: i + 1]


class TzktDatasource(IndexDatasource):
    """Bridge between REST/WS TzKT endpoints and DipDup.

    * Converts raw API data to models
    * Handles WS interaction to manage subscriptions
    * Calls Fetchers to synchronize indexes to current head
    * Calls Matchers to match received operation groups with indexes' pattern and spawn callbacks on match
    """

    def __init__(
        self,
        url: str,
        http_config: Optional[HTTPConfig] = None,
    ) -> None:
        super().__init__(url, http_config)
        self._logger = logging.getLogger('dipdup.tzkt')

        self._transaction_subscriptions: Set[str] = set()
        self._origination_subscriptions: bool = False
        self._big_map_subscriptions: Dict[str, Set[str]] = {}
        self._client: Optional[BaseHubConnection] = None

        self._block: Optional[HeadBlockData] = None
        self._level: Optional[int] = None
        self._sync_level: Optional[int] = None

    @property
    def request_limit(self) -> int:
        return self._http_config.batch_size or 10000

    @property
    def level(self) -> Optional[int]:
        return self._level

    @property
    def sync_level(self) -> Optional[int]:
        return self._sync_level

    @property
    def block(self) -> HeadBlockData:
        if self._block is None:
            raise RuntimeError('No message from `head` channel received')
        return self._block

    async def get_similar_contracts(self, address: str, strict: bool = False) -> List[str]:
        """Get list of contracts sharing the same code hash or type hash"""
        entrypoint = 'same' if strict else 'similar'
        self._logger.info('Fetching %s contracts for address `%s', entrypoint, address)

        contracts = await self._http.request(
            'get',
            url=f'v1/contracts/{address}/{entrypoint}',
            params=dict(
                select='address',
                limit=self.request_limit,
            ),
        )
        return contracts

    async def get_originated_contracts(self, address: str) -> List[str]:
        """Get contracts originated from given address"""
        self._logger.info('Fetching originated contracts for address `%s', address)
        contracts = await self._http.request(
            'get',
            url=f'v1/accounts/{address}/contracts',
            params=dict(
                limit=self.request_limit,
            ),
        )
        return [c['address'] for c in contracts]

    async def get_contract_summary(self, address: str) -> Dict[str, Any]:
        """Get contract summary"""
        self._logger.info('Fetching contract summary for address `%s', address)
        return await self._http.request(
            'get',
            url=f'v1/contracts/{address}',
        )

    async def get_contract_storage(self, address: str) -> Dict[str, Any]:
        """Get contract storage"""
        self._logger.info('Fetching contract storage for address `%s', address)
        return await self._http.request(
            'get',
            url=f'v1/contracts/{address}/storage',
        )

    async def get_jsonschemas(self, address: str) -> Dict[str, Any]:
        """Get JSONSchemas for contract's storage/parameter/bigmap types"""
        self._logger.info('Fetching jsonschemas for address `%s', address)
        jsonschemas = await self._http.request(
            'get',
            url=f'v1/contracts/{address}/interface',
            cache=True,
        )
        self._logger.debug(jsonschemas)
        return jsonschemas

    async def get_head_block(self) -> HeadBlockData:
        """Get latest block (head)"""
        self._logger.info('Fetching latest block')
        head_block_json = await self._http.request(
            'get',
            url='v1/head',
        )
        return self.convert_head_block(head_block_json)

    async def get_block(self, level: int) -> BlockData:
        """Get block by level"""
        self._logger.info('Fetching block %s', level)
        block_json = await self._http.request(
            'get',
            url=f'v1/blocks/{level}',
        )
        return self.convert_block(block_json)

    async def get_migration_originations(self, first_level: int = 0) -> List[OperationData]:
        """Get contracts originated from migrations"""
        self._logger.info('Fetching contracts originated with migrations')
        # NOTE: Empty unwrapped request to ensure API supports migration originations
        try:
            await self._http._request(
                'get',
                url='v1/operations/migrations',
                params={
                    'kind': 'origination',
                    'limit': 0,
                },
            )
        except ClientResponseError:
            return []

        raw_migrations = await self._http.request(
            'get',
            url='v1/operations/migrations',
            params={
                'kind': 'origination',
                'level.gt': first_level,
                'select': ','.join(ORIGINATION_MIGRATION_FIELDS),
            },
        )
        return [self.convert_migration_origination(m) for m in raw_migrations]

    async def get_originations(
        self, addresses: Set[str], offset: int, first_level: int, last_level: int, cache: bool = False
    ) -> List[OperationData]:
        raw_originations = []
        # NOTE: TzKT may hit URL length limit with hundreds of originations in a single request.
        # NOTE: Chunk of 100 addresses seems like a reasonable choice - URL of ~3971 characters.
        # NOTE: Other operation requests won't hit that limit.
        for addresses_chunk in split_by_chunks(list(addresses), TZKT_ORIGINATIONS_REQUEST_LIMIT):
            raw_originations += await self._http.request(
                'get',
                url='v1/operations/originations',
                params={
                    "originatedContract.in": ','.join(addresses_chunk),
                    "offset": offset,
                    "limit": self.request_limit,
                    "level.gt": first_level,
                    "level.le": last_level,
                    "select": ','.join(ORIGINATION_OPERATION_FIELDS),
                    "status": "applied",
                },
                cache=cache,
            )

        originations = []
        for op in raw_originations:
            # NOTE: `type` field needs to be set manually when requesting operations by specific type
            op['type'] = 'origination'
            originations.append(self.convert_operation(op))
        return originations

    async def get_transactions(
        self, field: str, addresses: Set[str], offset: int, first_level: int, last_level: int, cache: bool = False
    ) -> List[OperationData]:
        raw_transactions = await self._http.request(
            'get',
            url='v1/operations/transactions',
            params={
                f"{field}.in": ','.join(addresses),
                "offset": offset,
                "limit": self.request_limit,
                "level.gt": first_level,
                "level.le": last_level,
                "select": ','.join(TRANSACTION_OPERATION_FIELDS),
                "status": "applied",
            },
            cache=cache,
        )
        transactions = []
        for op in raw_transactions:
            # NOTE: type needs to be set manually when requesting operations by specific type
            op['type'] = 'transaction'
            transactions.append(self.convert_operation(op))
        return transactions

    async def get_big_maps(
        self, addresses: Set[str], paths: Set[str], offset: int, first_level: int, last_level: int, cache: bool = False
    ) -> List[BigMapData]:
        raw_big_maps = await self._http.request(
            'get',
            url='v1/bigmaps/updates',
            params={
                "contract.in": ",".join(addresses),
                "paths.in": ",".join(paths),
                "offset": offset,
                "limit": self.request_limit,
                "level.gt": first_level,
                "level.le": last_level,
            },
            cache=cache,
        )
        big_maps = []
        for bm in raw_big_maps:
            big_maps.append(self.convert_big_map(bm))
        return big_maps

    async def add_index(self, index_config: IndexConfigTemplateT) -> None:
        """Register index config in internal mappings and matchers. Find and register subscriptions."""

        if isinstance(index_config, OperationIndexConfig):
            for contract_config in index_config.contracts or []:
                self._transaction_subscriptions.add(cast(ContractConfig, contract_config).address)
            for handler_config in index_config.handlers:
                for pattern_config in handler_config.pattern:
                    if isinstance(pattern_config, OperationHandlerOriginationPatternConfig):
                        self._origination_subscriptions = True

        elif isinstance(index_config, BigMapIndexConfig):
            for big_map_handler_config in index_config.handlers:
                address, path = big_map_handler_config.contract_config.address, big_map_handler_config.path
                if address not in self._big_map_subscriptions:
                    self._big_map_subscriptions[address] = set()
                if path not in self._big_map_subscriptions[address]:
                    self._big_map_subscriptions[address].add(path)

        else:
            raise NotImplementedError(f'Index kind `{index_config.kind}` is not supported')

        await self._on_connect()

    def _get_client(self) -> BaseHubConnection:
        """Create SignalR client, register message callbacks"""
        if self._client is None:
            self._logger.info('Creating websocket client')
            self._client = (
                HubConnectionBuilder()
                .with_url(self._http._url + '/v1/events')
                .with_automatic_reconnect(
                    {
                        "type": "raw",
                        "keep_alive_interval": 10,
                        "reconnect_interval": 5,
                        "max_attempts": 5,
                    }
                )
            ).build()

            self._client.on_open(self._on_connect)
            self._client.on_error(self._on_error)
            self._client.on('operations', self._on_operation_message)
            self._client.on('bigmaps', self._on_big_map_message)
            self._client.on('head', self._on_head_message)

        return self._client

    async def run(self) -> None:
        """Main loop. Sync indexes via REST, start WS connection"""
        # TODO: Update docs, honor `realtime` flag
        self._logger.info('Starting datasource')

        self._logger.info('Starting websocket client')
        await self._get_client().start()

    async def _on_connect(self) -> None:
        """Subscribe to all required channels on established WS connection"""
        if self._get_client().transport.state != ConnectionState.connected:
            return

        self._logger.info('Connected to server')
        await self._subscribe_to_head()
        for address in self._transaction_subscriptions:
            await self._subscribe_to_transactions(address)
        # NOTE: All originations are passed to matcher
        if self._origination_subscriptions:
            await self._subscribe_to_originations()
        for address, paths in self._big_map_subscriptions.items():
            await self._subscribe_to_big_maps(address, paths)

    # NOTE: Pay attention: this is not a pyee callback
    def _on_error(self, message: CompletionMessage) -> NoReturn:
        """Raise exception from WS server's error message"""
        raise Exception(message.error)

    # TODO: Catch exceptions from pyee 'error' channel

    async def _subscribe_to_transactions(self, address: str) -> None:
        """Subscribe to contract's operations on established WS connection"""
        self._logger.info('Subscribing to %s transactions', address)
        await self._send(
            'SubscribeToOperations',
            [
                {
                    'address': address,
                    'types': 'transaction',
                }
            ],
        )

    async def _subscribe_to_originations(self) -> None:
        """Subscribe to all originations on established WS connection"""
        self._logger.info('Subscribing to originations')
        await self._send(
            'SubscribeToOperations',
            [
                {
                    'types': 'origination',
                }
            ],
        )

    async def _subscribe_to_big_maps(self, address: str, paths: Set[str]) -> None:
        """Subscribe to contract's big map diffs on established WS connection"""
        self._logger.info('Subscribing to big map updates of %s, %s', address, paths)
        for path in paths:
            await self._send(
                'SubscribeToBigMaps',
                [
                    {
                        'address': address,
                        'path': path,
                    }
                ],
            )

    async def _subscribe_to_head(self) -> None:
        """Subscribe to head on established WS connection"""
        self._logger.info('Subscribing to head')
        await self._send(
            'SubscribeToHead',
            [],
        )

    def _default_http_config(self) -> HTTPConfig:
        return HTTPConfig(
            cache=True,
            retry_sleep=1,
            retry_multiplier=1.1,
            ratelimit_rate=100,
            ratelimit_period=30,
            connection_limit=25,
        )

    async def _on_operation_message(self, message: List[Dict[str, Any]]) -> None:
        """Parse and emit raw operations from WS"""
        for item in message:
            current_level = item['state']
            message_type = TzktMessageType(item['type'])
            self._logger.info('Got operation message, %s, level %s', message_type, current_level)

            if message_type == TzktMessageType.STATE:
                self._sync_level = current_level
                self._level = current_level

            elif message_type == TzktMessageType.DATA:
                self._level = current_level
                operations = []
                for operation_json in item['data']:
                    operation = self.convert_operation(operation_json)
                    if operation.status != 'applied':
                        continue
                    operations.append(operation)
                if operations:
                    self.emit_operations(operations, self.block)

            elif message_type == TzktMessageType.REORG:
                if self.level is None:
                    raise RuntimeError
                self.emit_rollback(self.level, current_level)

            else:
                raise NotImplementedError

    async def _on_big_map_message(self, message: List[Dict[str, Any]]) -> None:
        """Parse and emit raw big map diffs from WS"""
        for item in message:
            current_level = item['state']
            message_type = TzktMessageType(item['type'])
            self._logger.info('Got big map message, %s, level %s', message_type, current_level)

            if message_type == TzktMessageType.STATE:
                self._sync_level = current_level
                self._level = current_level

            elif message_type == TzktMessageType.DATA:
                self._level = current_level
                big_maps = []
                for big_map_json in item['data']:
                    big_map = self.convert_big_map(big_map_json)
                    big_maps.append(big_map)
                self.emit_big_maps(big_maps)

            elif message_type == TzktMessageType.REORG:
                if self.level is None:
                    raise RuntimeError
                self.emit_rollback(self.level, current_level)

            else:
                raise NotImplementedError

    async def _on_head_message(self, message: List[Dict[str, Any]]) -> None:
        for item in message:
            current_level = item['state']
            message_type = TzktMessageType(item['type'])
            self._logger.info('Got block message, %s, level %s', message_type, current_level)

            if message_type == TzktMessageType.STATE:
                self._sync_level = current_level
                self._level = current_level

            elif message_type == TzktMessageType.DATA:
                self._level = current_level
                block_json = item['data']
                block = self.convert_head_block(block_json)
                self._block = block
                self.emit_head(block)

            elif message_type == TzktMessageType.REORG:
                if self.level is None:
                    raise RuntimeError
                self.emit_rollback(self.level, current_level)

            else:
                raise NotImplementedError

    @classmethod
    def convert_operation(cls, operation_json: Dict[str, Any]) -> OperationData:
        """Convert raw operation message from WS/REST into dataclass"""
        storage = operation_json.get('storage')
        # FIXME: Plain storage, has issues in codegen: KT1CpeSQKdkhWi4pinYcseCFKmDhs5M74BkU
        if not isinstance(storage, Dict):
            storage = {}

        return OperationData(
            type=operation_json['type'],
            id=operation_json['id'],
            level=operation_json['level'],
            timestamp=cls._parse_timestamp(operation_json['timestamp']),
            block=operation_json.get('block'),
            hash=operation_json['hash'],
            counter=operation_json['counter'],
            sender_address=operation_json['sender']['address'] if operation_json.get('sender') else None,
            target_address=operation_json['target']['address'] if operation_json.get('target') else None,
            initiator_address=operation_json['initiator']['address'] if operation_json.get('initiator') else None,
            amount=operation_json.get('amount') or operation_json.get('contractBalance'),
            status=operation_json['status'],
            has_internals=operation_json.get('hasInternals'),
            sender_alias=operation_json['sender'].get('alias'),
            nonce=operation_json.get('nonce'),
            target_alias=operation_json['target'].get('alias') if operation_json.get('target') else None,
            initiator_alias=operation_json['initiator'].get('alias') if operation_json.get('initiator') else None,
            entrypoint=operation_json['parameter'].get('entrypoint') if operation_json.get('parameter') else None,
            parameter_json=operation_json['parameter'].get('value') if operation_json.get('parameter') else None,
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
    def convert_migration_origination(cls, migration_origination_json: Dict[str, Any]) -> OperationData:
        """Convert raw migration message from REST into dataclass"""
        storage = migration_origination_json.get('storage')
        # FIXME: Plain storage, has issues in codegen: KT1CpeSQKdkhWi4pinYcseCFKmDhs5M74BkU
        if not isinstance(storage, Dict):
            storage = {}

        fake_operation_data = OperationData(
            type='origination',
            id=migration_origination_json['id'],
            level=migration_origination_json['level'],
            timestamp=cls._parse_timestamp(migration_origination_json['timestamp']),
            block=migration_origination_json.get('block'),
            originated_contract_address=migration_origination_json['account']['address'],
            originated_contract_alias=migration_origination_json['account'].get('alias'),
            amount=migration_origination_json['balanceChange'],
            storage=storage,
            diffs=migration_origination_json.get('diffs'),
            status='applied',
            has_internals=False,
            hash='[none]',
            counter=0,
            sender_address='[none]',
            target_address=None,
            initiator_address=None,
        )
        return fake_operation_data

    @classmethod
    def convert_big_map(cls, big_map_json: Dict[str, Any]) -> BigMapData:
        """Convert raw big map diff message from WS/REST into dataclass"""
        return BigMapData(
            id=big_map_json['id'],
            level=big_map_json['level'],
            # FIXME: operation_id field in API
            operation_id=big_map_json['level'],
            timestamp=cls._parse_timestamp(big_map_json['timestamp']),
            bigmap=big_map_json['bigmap'],
            contract_address=big_map_json['contract']['address'],
            path=big_map_json['path'],
            action=BigMapAction(big_map_json['action']),
            key=big_map_json.get('content', {}).get('key'),
            value=big_map_json.get('content', {}).get('value'),
        )

    @classmethod
    def convert_block(cls, block_json: Dict[str, Any]) -> BlockData:
        """Convert raw block message from REST into dataclass"""
        return BlockData(
            level=block_json['level'],
            hash=block_json['hash'],
            timestamp=cls._parse_timestamp(block_json['timestamp']),
            proto=block_json['proto'],
            priority=block_json['priority'],
            validations=block_json['validations'],
            deposit=block_json['deposit'],
            reward=block_json['reward'],
            fees=block_json['fees'],
            nonce_revealed=block_json['nonceRevealed'],
            baker_address=block_json.get('baker', {}).get('address'),
            baker_alias=block_json.get('baker', {}).get('alias'),
        )

    @classmethod
    def convert_head_block(cls, head_block_json: Dict[str, Any]) -> HeadBlockData:
        """Convert raw head block message from WS/REST into dataclass"""
        return HeadBlockData(
            cycle=head_block_json['cycle'],
            level=head_block_json['level'],
            hash=head_block_json['hash'],
            protocol=head_block_json['protocol'],
            timestamp=cls._parse_timestamp(head_block_json['timestamp']),
            voting_epoch=head_block_json['votingEpoch'],
            voting_period=head_block_json['votingPeriod'],
            known_level=head_block_json['knownLevel'],
            last_sync=head_block_json['lastSync'],
            synced=head_block_json['synced'],
            quote_level=head_block_json['quoteLevel'],
            quote_btc=Decimal(head_block_json['quoteBtc']),
            quote_eur=Decimal(head_block_json['quoteEur']),
            quote_usd=Decimal(head_block_json['quoteUsd']),
            quote_cny=Decimal(head_block_json['quoteCny']),
            quote_jpy=Decimal(head_block_json['quoteJpy']),
            quote_krw=Decimal(head_block_json['quoteKrw']),
            quote_eth=Decimal(head_block_json['quoteEth']),
        )

    async def _send(self, method: str, arguments: List[Dict[str, Any]], on_invocation=None) -> None:
        client = self._get_client()
        while client.transport.state != ConnectionState.connected:
            await asyncio.sleep(0.1)
        await client.send(method, arguments, on_invocation)

    @classmethod
    def _parse_timestamp(cls, timestamp: str) -> datetime:
        return datetime.fromisoformat(timestamp[:-1]).replace(tzinfo=timezone.utc)
