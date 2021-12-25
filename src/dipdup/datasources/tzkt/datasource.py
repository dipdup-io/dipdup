import asyncio
import logging
from asyncio import Event
from asyncio import create_task
from asyncio import gather
from collections import defaultdict
from collections import deque
from datetime import datetime
from datetime import timezone
from decimal import Decimal
from typing import Any
from typing import AsyncGenerator
from typing import Awaitable
from typing import Callable
from typing import DefaultDict
from typing import Deque
from typing import Dict
from typing import List
from typing import NoReturn
from typing import Optional
from typing import Set
from typing import Tuple
from typing import cast

from aiohttp import ClientResponseError
from pysignalr.client import SignalRClient
from pysignalr.messages import CompletionMessage  # type: ignore
from pysignalr.transport.websocket import DEFAULT_MAX_SIZE

from dipdup.config import HTTPConfig
from dipdup.config import ResolvedIndexConfigT
from dipdup.datasources.datasource import IndexDatasource
from dipdup.datasources.subscription import BigMapSubscription
from dipdup.datasources.subscription import HeadSubscription
from dipdup.datasources.subscription import OriginationSubscription
from dipdup.datasources.subscription import Subscription
from dipdup.datasources.subscription import TransactionSubscription
from dipdup.datasources.tzkt.enums import ORIGINATION_MIGRATION_FIELDS
from dipdup.datasources.tzkt.enums import ORIGINATION_OPERATION_FIELDS
from dipdup.datasources.tzkt.enums import TRANSACTION_OPERATION_FIELDS
from dipdup.datasources.tzkt.enums import OperationFetcherRequest
from dipdup.datasources.tzkt.enums import TzktMessageType
from dipdup.enums import MessageType
from dipdup.exceptions import DatasourceError
from dipdup.models import BigMapAction
from dipdup.models import BigMapData
from dipdup.models import BlockData
from dipdup.models import HeadBlockData
from dipdup.models import OperationData
from dipdup.models import QuoteData
from dipdup.utils import split_by_chunks
from dipdup.utils.watchdog import Watchdog

TZKT_ORIGINATIONS_REQUEST_LIMIT = 100


def dedup_operations(operations: Tuple[OperationData, ...]) -> Tuple[OperationData, ...]:
    """Merge and sort operations fetched from multiple endpoints"""
    return tuple(
        sorted(
            tuple(({op.id: op for op in operations}).values()),
            key=lambda op: op.id,
        )
    )


class OperationFetcher:
    """Fetches operations from multiple REST API endpoints, merges them and yields by level. Offet of every endpoint is tracked separately."""

    def __init__(
        self,
        datasource: 'TzktDatasource',
        first_level: int,
        last_level: int,
        transaction_addresses: Set[str],
        origination_addresses: Set[str],
        cache: bool = False,
        migration_originations: Tuple[OperationData, ...] = None,
    ) -> None:
        self._datasource = datasource
        self._first_level = first_level
        self._last_level = last_level
        self._transaction_addresses = transaction_addresses
        self._origination_addresses = origination_addresses
        self._cache = cache

        self._logger = logging.getLogger('dipdup.tzkt')
        self._head: int = 0
        self._heads: Dict[OperationFetcherRequest, int] = {}
        self._offsets: Dict[OperationFetcherRequest, int] = {}
        self._fetched: Dict[OperationFetcherRequest, bool] = {}

        self._operations: DefaultDict[int, Deque[OperationData]] = defaultdict(deque)
        for origination in migration_originations or ():
            self._operations[origination.level].append(origination)

    def _get_operations_head(self, operations: Tuple[OperationData, ...]) -> int:
        """Get latest block level (head) of sorted operations batch"""
        for i in range(len(operations) - 1)[::-1]:
            if operations[i].level != operations[i + 1].level:
                return operations[i].level
        return operations[0].level

    async def _fetch_originations(self) -> None:
        """Fetch a single batch of originations, bump channel offset"""
        key = OperationFetcherRequest.originations
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
        key = getattr(OperationFetcherRequest, field + '_transactions')
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
            self._operations[level].append(op)

        self._logger.debug('Got %s', len(transactions))

        if len(transactions) < self._datasource.request_limit:
            self._fetched[key] = True
            self._heads[key] = self._last_level
        else:
            self._offsets[key] += self._datasource.request_limit
            self._heads[key] = self._get_operations_head(transactions)

    async def fetch_operations_by_level(self) -> AsyncGenerator[Tuple[int, Tuple[OperationData, ...]], None]:
        """Iterate over operations fetched with multiple REST requests with different filters.

        Resulting data is splitted by level, deduped, sorted and ready to be processed by OperationIndex.
        """
        for type_ in (
            OperationFetcherRequest.sender_transactions,
            OperationFetcherRequest.target_transactions,
            OperationFetcherRequest.originations,
        ):
            self._heads[type_] = 0
            self._offsets[type_] = 0
            self._fetched[type_] = False

        while True:
            min_head = sorted(self._heads.items(), key=lambda x: x[1])[0][0]
            if min_head == OperationFetcherRequest.originations:
                await self._fetch_originations()
            elif min_head == OperationFetcherRequest.target_transactions:
                await self._fetch_transactions('target')
            elif min_head == OperationFetcherRequest.sender_transactions:
                await self._fetch_transactions('sender')
            else:
                raise RuntimeError

            head = min(self._heads.values())
            while self._head <= head:
                if self._head in self._operations:
                    operations = self._operations.pop(self._head)
                    yield self._head, dedup_operations(tuple(operations))
                self._head += 1

            if all(self._fetched.values()):
                break

        if self._operations:
            raise RuntimeError('Operations left in queue')


class BigMapFetcher:
    """Fetches bigmap diffs from REST API, merges them and yields by level."""

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

    async def fetch_big_maps_by_level(self) -> AsyncGenerator[Tuple[int, Tuple[BigMapData, ...]], None]:
        """Iterate over big map diffs fetched fetched from REST.

        Resulting data is splitted by level, deduped, sorted and ready to be processed by BigMapIndex.
        """

        offset = 0
        big_maps: Tuple[BigMapData, ...] = tuple()

        # TODO: Share code between this and OperationFetcher
        while True:
            fetched_big_maps = await self._datasource.get_big_maps(
                self._big_map_addresses,
                self._big_map_paths,
                offset,
                self._first_level,
                self._last_level,
                cache=self._cache,
            )
            big_maps = big_maps + fetched_big_maps

            # NOTE: Yield big map slices by level except the last one
            while True:
                for i in range(len(big_maps) - 1):
                    curr_level, next_level = big_maps[i].level, big_maps[i + 1].level

                    # NOTE: Level boundaries found. Exit for loop, stay in while.
                    if curr_level != next_level:
                        yield curr_level, big_maps[: i + 1]
                        big_maps = big_maps[i + 1 :]
                        break
                else:
                    break

            if len(fetched_big_maps) < self._datasource.request_limit:
                break

            offset += self._datasource.request_limit

        if big_maps:
            yield big_maps[0].level, big_maps


class TzktDatasource(IndexDatasource):
    _default_http_config = HTTPConfig(
        cache=True,
        retry_sleep=1,
        retry_multiplier=2,
        ratelimit_rate=100,
        ratelimit_period=1,
        connection_limit=25,
        batch_size=1000,
    )

    def __init__(
        self,
        url: str,
        http_config: Optional[HTTPConfig] = None,
        watchdog: Optional[Watchdog] = None,
        merge_subscriptions: bool = False,
    ) -> None:
        super().__init__(
            url=url,
            http_config=self._default_http_config.merge(http_config),
            merge_subscriptions=merge_subscriptions,
        )
        self._logger = logging.getLogger('dipdup.tzkt')
        self._watchdog = watchdog

        self._ws_client: Optional[SignalRClient] = None
        self._level: DefaultDict[MessageType, Optional[int]] = defaultdict(lambda: None)

    @property
    def request_limit(self) -> int:
        return cast(int, self._http_config.batch_size)

    async def get_similar_contracts(self, address: str, strict: bool = False) -> Tuple[str, ...]:
        """Get addresses of contracts that share the same code hash or type hash"""
        entrypoint = 'same' if strict else 'similar'
        self._logger.info('Fetching %s contracts for address `%s`', entrypoint, address)

        size, offset = self.request_limit, 0
        addresses: Tuple[str, ...] = tuple()

        while size == self.request_limit:
            response = await self._http.request(
                'get',
                url=f'v1/contracts/{address}/{entrypoint}',
                params=dict(
                    select='address',
                    limit=self.request_limit,
                    offset=offset,
                ),
            )
            size = len(response)
            addresses = addresses + tuple(response)
            offset += self.request_limit

        return addresses

    async def get_originated_contracts(self, address: str) -> Tuple[str, ...]:
        """Get addresses of contracts originated from given address"""
        self._logger.info('Fetching originated contracts for address `%s', address)

        size, offset = self.request_limit, 0
        addresses: Tuple[str, ...] = tuple()

        while size == self.request_limit:
            response = await self._http.request(
                'get',
                url=f'v1/accounts/{address}/contracts',
                params=dict(
                    select='address',
                    limit=self.request_limit,
                    offset=offset,
                ),
            )
            size = len(response)
            addresses = addresses + tuple(c['address'] for c in response)
            offset += self.request_limit

        return addresses

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

    async def get_migration_originations(self, first_level: int = 0) -> Tuple[OperationData, ...]:
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
            return ()

        raw_migrations = await self._http.request(
            'get',
            url='v1/operations/migrations',
            params={
                'kind': 'origination',
                'level.gt': first_level,
                'select': ','.join(ORIGINATION_MIGRATION_FIELDS),
            },
        )
        return tuple(self.convert_migration_origination(m) for m in raw_migrations)

    async def get_originations(
        self, addresses: Set[str], offset: int, first_level: int, last_level: int, cache: bool = False
    ) -> Tuple[OperationData, ...]:
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

        # NOTE: `type` field needs to be set manually when requesting operations by specific type
        originations = tuple(self.convert_operation(op, type_='origination') for op in raw_originations)
        return originations

    async def get_transactions(
        self, field: str, addresses: Set[str], offset: int, first_level: int, last_level: int, cache: bool = False
    ) -> Tuple[OperationData, ...]:
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

        # NOTE: `type` field needs to be set manually when requesting operations by specific type
        transactions = tuple(self.convert_operation(op, type_='transaction') for op in raw_transactions)
        return transactions

    async def get_big_maps(
        self, addresses: Set[str], paths: Set[str], offset: int, first_level: int, last_level: int, cache: bool = False
    ) -> Tuple[BigMapData, ...]:
        raw_big_maps = await self._http.request(
            'get',
            url='v1/bigmaps/updates',
            params={
                "contract.in": ",".join(addresses),
                "path.in": ",".join(paths),
                "offset": offset,
                "limit": self.request_limit,
                "level.gt": first_level,
                "level.le": last_level,
            },
            cache=cache,
        )
        big_maps = tuple(self.convert_big_map(bm) for bm in raw_big_maps)
        return big_maps

    async def get_quote(self, level: int) -> QuoteData:
        """Get quote for block"""
        self._logger.info('Fetching quotes for level %s', level)
        quote_json = await self._http.request(
            'get',
            url='v1/quotes',
            params={"level": level},
            cache=True,
        )
        return self.convert_quote(quote_json[0])

    async def get_quotes(self, from_level: int, to_level: int) -> Tuple[QuoteData, ...]:
        """Get quotes for blocks"""
        self._logger.info('Fetching quotes for levels %s-%s', from_level, to_level)
        quotes_json = await self._http.request(
            'get',
            url='v1/quotes',
            params={
                "level.ge": from_level,
                "level.lt": to_level,
                "limit": self.request_limit,
            },
            cache=False,
        )
        return tuple(self.convert_quote(quote) for quote in quotes_json)

    async def add_index(self, index_config: ResolvedIndexConfigT) -> None:
        """Register index config in internal mappings and matchers. Find and register subscriptions."""
        for subscription in index_config.subscriptions:
            self._subscriptions.add(subscription)

    async def subscribe(self) -> None:
        missing_subscriptions = self._subscriptions.missing_subscriptions
        if not missing_subscriptions:
            return

        self._logger.info('Subscribing to %s channels', len(missing_subscriptions))
        tasks = (self._subscribe(subscription) for subscription in missing_subscriptions)
        await asyncio.gather(*tasks)
        self._logger.info('Subscribed to %s channels', len(missing_subscriptions))

    async def _subscribe(self, subscription: Subscription) -> None:
        self._logger.debug('Subscribing to %s', subscription)
        request: List[Dict[str, Any]]

        if isinstance(subscription, TransactionSubscription):
            method = 'SubscribeToOperations'
            request = [{'types': 'transaction'}]
            if subscription.address:
                request[0]['address'] = subscription.address

        elif isinstance(subscription, OriginationSubscription):
            method = 'SubscribeToOperations'
            request = [{'types': 'origination'}]

        elif isinstance(subscription, HeadSubscription):
            method, request = 'SubscribeToHead', []

        elif isinstance(subscription, BigMapSubscription):
            method = 'SubscribeToBigMaps'
            if subscription.address and subscription.path:
                request = [{'address': subscription.address, 'paths': [subscription.path]}]
            elif not subscription.address and not subscription.path:
                request = [{}]
            else:
                raise RuntimeError

        else:
            raise NotImplementedError

        event = Event()

        async def _on_subscribe(message: CompletionMessage) -> None:
            if message.error:
                await self._on_error(message)
            level = cast(int, message.result)
            self._subscriptions.set_sync_level(subscription, level)
            event.set()

        await self._send(method, request, _on_subscribe)
        await event.wait()

    def _get_ws_client(self) -> SignalRClient:
        """Create SignalR client, register message callbacks"""
        if self._ws_client:
            return self._ws_client

        self._logger.info('Creating websocket client')
        self._ws_client = SignalRClient(
            url=f'{self._http._url}/v1/events',
            # NOTE: 1 MB default is not enough for big blocks
            max_size=DEFAULT_MAX_SIZE * 10,
        )

        self._ws_client.on_open(self._on_connect)
        self._ws_client.on_close(self._on_disconnect)
        self._ws_client.on_error(self._on_error)

        self._ws_client.on('operations', self._on_operations_message)
        self._ws_client.on('bigmaps', self._on_big_maps_message)
        self._ws_client.on('head', self._on_head_message)

        return self._ws_client

    async def run(self) -> None:
        self._logger.info('Establishing realtime connection')
        tasks = [create_task(self._get_ws_client().run())]

        if self._watchdog:
            tasks.append(create_task(self._watchdog.run()))

        await gather(*tasks)

    async def _on_connect(self) -> None:
        """Subscribe to all required channels on established WS connection"""
        self._logger.info('Realtime connection established')
        # NOTE: Subscribing here will block WebSocket loop
        # await self.subscribe()

    async def _on_disconnect(self) -> None:
        self._logger.info('Realtime connection lost')
        self._subscriptions.reset()

    async def _on_error(self, message: CompletionMessage) -> NoReturn:
        """Raise exception from WS server's error message"""
        raise DatasourceError(datasource=self.name, msg=cast(str, message.error))

    async def _extract_message_data(self, type_: MessageType, message: List[Any]) -> AsyncGenerator[Dict, None]:
        """Parse message received from Websocket, ensure it's correct in the current context and yield data."""
        for item in message:
            tzkt_type = TzktMessageType(item['type'])
            if tzkt_type == TzktMessageType.STATE:
                continue

            level, current_level = item['state'], self._level[type_]
            self._level[type_] = level
            self._logger.info('Realtime message received: %s, %s, %s -> %s', type_.value, tzkt_type.name, current_level, level)

            # NOTE: Just yield data
            if tzkt_type == TzktMessageType.DATA:
                yield item['data']

            # NOTE: Emit rollback, but not on `head` message
            elif tzkt_type == TzktMessageType.REORG:
                if current_level is None:
                    raise RuntimeError('Reorg message received but level is not set')
                # NOTE: operation/big_map channels have their own levels
                if type_ == MessageType.head:
                    return

                self._logger.info('Emitting rollback from %s to %s', current_level, level)
                await self.emit_rollback(current_level, level)

            else:
                raise NotImplementedError

    async def _on_operations_message(self, message: List[Dict[str, Any]]) -> None:
        """Parse and emit raw operations from WS"""
        async for data in self._extract_message_data(MessageType.operation, message):
            operations: Deque[OperationData] = deque()
            for operation_json in data:
                if operation_json['status'] != 'applied':
                    continue
                operation = self.convert_operation(operation_json)
                operations.append(operation)
            if operations:
                await self.emit_operations(tuple(operations))

    async def _on_big_maps_message(self, message: List[Dict[str, Any]]) -> None:
        """Parse and emit raw big map diffs from WS"""
        async for data in self._extract_message_data(MessageType.big_map, message):
            big_maps: Deque[BigMapData] = deque()
            for big_map_json in data:
                big_map = self.convert_big_map(big_map_json)
                big_maps.append(big_map)
            await self.emit_big_maps(tuple(big_maps))

    async def _on_head_message(self, message: List[Dict[str, Any]]) -> None:
        """Parse and emit raw head block from WS"""
        async for data in self._extract_message_data(MessageType.head, message):
            if self._watchdog:
                self._watchdog.reset()

            block = self.convert_head_block(data)
            await self.emit_head(block)

    @classmethod
    def convert_operation(cls, operation_json: Dict[str, Any], type_: Optional[str] = None) -> OperationData:
        """Convert raw operation message from WS/REST into dataclass"""
        sender_json = operation_json.get('sender') or {}
        target_json = operation_json.get('target') or {}
        initiator_json = operation_json.get('initiator') or {}
        parameter_json = operation_json.get('parameter') or {}
        originated_contract_json = operation_json.get('originatedContract') or {}

        entrypoint, parameter = parameter_json.get('entrypoint'), parameter_json.get('value')
        # NOTE: TzKT returns None for `default` entrypoint
        if entrypoint is None and parameter_json:
            entrypoint = 'default'

        return OperationData(
            type=type_ or operation_json['type'],
            id=operation_json['id'],
            level=operation_json['level'],
            timestamp=cls._parse_timestamp(operation_json['timestamp']),
            block=operation_json.get('block'),
            hash=operation_json['hash'],
            counter=operation_json['counter'],
            sender_address=sender_json.get('address'),
            target_address=target_json.get('address'),
            initiator_address=initiator_json.get('address'),
            amount=operation_json.get('amount') or operation_json.get('contractBalance'),
            status=operation_json['status'],
            has_internals=operation_json.get('hasInternals'),
            sender_alias=operation_json['sender'].get('alias'),
            nonce=operation_json.get('nonce'),
            target_alias=target_json.get('alias'),
            initiator_alias=initiator_json.get('alias'),
            entrypoint=entrypoint,
            parameter_json=parameter,
            originated_contract_address=originated_contract_json.get('address'),
            originated_contract_type_hash=originated_contract_json.get('typeHash'),
            originated_contract_code_hash=originated_contract_json.get('codeHash'),
            storage=operation_json.get('storage'),
            diffs=operation_json.get('diffs') or (),
        )

    @classmethod
    def convert_migration_origination(cls, migration_origination_json: Dict[str, Any]) -> OperationData:
        """Convert raw migration message from REST into dataclass"""
        return OperationData(
            type='origination',
            id=migration_origination_json['id'],
            level=migration_origination_json['level'],
            timestamp=cls._parse_timestamp(migration_origination_json['timestamp']),
            block=migration_origination_json.get('block'),
            originated_contract_address=migration_origination_json['account']['address'],
            originated_contract_alias=migration_origination_json['account'].get('alias'),
            amount=migration_origination_json['balanceChange'],
            storage=migration_origination_json.get('storage'),
            diffs=migration_origination_json.get('diffs') or (),
            status='applied',
            has_internals=False,
            hash='[none]',
            counter=0,
            sender_address='[none]',
            target_address=None,
            initiator_address=None,
        )

    @classmethod
    def convert_big_map(cls, big_map_json: Dict[str, Any]) -> BigMapData:
        """Convert raw big map diff message from WS/REST into dataclass"""
        return BigMapData(
            id=big_map_json['id'],
            level=big_map_json['level'],
            # FIXME: missing `operation_id` field in API to identify operation
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

    @classmethod
    def convert_quote(cls, quote_json: Dict[str, Any]) -> QuoteData:
        """Convert raw quote message from REST into dataclass"""
        return QuoteData(
            level=quote_json['level'],
            timestamp=cls._parse_timestamp(quote_json['timestamp']),
            btc=Decimal(quote_json['btc']),
            eur=Decimal(quote_json['eur']),
            usd=Decimal(quote_json['usd']),
            cny=Decimal(quote_json['cny']),
            jpy=Decimal(quote_json['jpy']),
            krw=Decimal(quote_json['krw']),
            eth=Decimal(quote_json['eth']),
        )

    async def _send(
        self,
        method: str,
        arguments: List[Dict[str, Any]],
        on_invocation: Optional[Callable[[CompletionMessage], Awaitable[None]]] = None,
    ) -> None:
        client = self._get_ws_client()
        await client.send(method, arguments, on_invocation)

    @classmethod
    def _parse_timestamp(cls, timestamp: str) -> datetime:
        return datetime.fromisoformat(timestamp[:-1]).replace(tzinfo=timezone.utc)
