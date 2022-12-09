import asyncio
import logging
import sys
from asyncio import Event
from asyncio import create_task
from collections import defaultdict
from collections import deque
from datetime import datetime
from datetime import timezone
from decimal import Decimal
from enum import Enum
from functools import partial
from typing import Any
from typing import AsyncIterator
from typing import Awaitable
from typing import Callable
from typing import Generator
from typing import NamedTuple
from typing import NoReturn
from typing import Sequence
from typing import cast

from pysignalr.client import SignalRClient
from pysignalr.exceptions import ConnectionError as WebsocketConnectionError
from pysignalr.messages import CompletionMessage

from dipdup import baking_bad
from dipdup.config import HTTPConfig
from dipdup.config import ResolvedIndexConfigU
from dipdup.datasources.datasource import IndexDatasource
from dipdup.datasources.subscription import Subscription
from dipdup.datasources.tzkt.models import HeadSubscription
from dipdup.enums import MessageType
from dipdup.enums import TokenStandard
from dipdup.exceptions import DatasourceError
from dipdup.exceptions import FrameworkException
from dipdup.models import BigMapAction
from dipdup.models import BigMapData
from dipdup.models import BlockData
from dipdup.models import EventData
from dipdup.models import HeadBlockData
from dipdup.models import OperationData
from dipdup.models import QuoteData
from dipdup.models import TokenTransferData
from dipdup.utils import FormattedLogger
from dipdup.utils import split_by_chunks

ORIGINATION_REQUEST_LIMIT = 100
OPERATION_FIELDS = (
    'type',
    'id',
    'level',
    'timestamp',
    'hash',
    'counter',
    'sender',
    'nonce',
    'target',
    'initiator',
    'amount',
    'storage',
    'status',
    'hasInternals',
    'diffs',
    'delegate',
    'senderCodeHash',
    'targetCodeHash',
)
ORIGINATION_MIGRATION_FIELDS = (
    'id',
    'level',
    'timestamp',
    'storage',
    'diffs',
    'account',
    'balanceChange',
)
ORIGINATION_OPERATION_FIELDS = (
    *OPERATION_FIELDS,
    'originatedContract',
)
TRANSACTION_OPERATION_FIELDS = (
    *OPERATION_FIELDS,
    'parameter',
    'hasInternals',
)


class TzktMessageType(Enum):
    STATE = 0
    DATA = 1
    REORG = 2


MessageData = dict[str, Any] | list[dict[str, Any]]


class BufferedMessage(NamedTuple):
    type: MessageType
    data: MessageData


class MessageBuffer:
    """Buffers realtime TzKT messages and yields them by level.

    Initially, it was a mitigation for TzKT's reorgs.
    """

    def __init__(self, size: int) -> None:
        self._logger = logging.getLogger('dipdup.tzkt')
        self._size = size
        self._messages: dict[int, list[BufferedMessage]] = {}

    def __len__(self) -> int:
        return len(self._messages)

    def add(self, type_: MessageType, level: int, data: MessageData) -> None:
        """Add a message to the buffer."""
        if level not in self._messages:
            self._messages[level] = []
        self._messages[level].append(BufferedMessage(type_, data))

    def rollback(self, type_: MessageType, channel_level: int, message_level: int) -> bool:
        """Drop buffered messages in reversed order while possible, return if successful."""
        self._logger.info('`%s` rollback requested: %s -> %s', type_.value, channel_level, message_level)
        levels = range(channel_level, message_level, -1)
        for level in levels:
            if level not in self._messages:
                return False

            for i, message in enumerate(self._messages[level]):
                if message.type == type_:
                    del self._messages[level][i]

        return True

    def yield_from(self) -> Generator[BufferedMessage, None, None]:
        """Yield extensively buffered messages by level"""
        buffered_levels = sorted(self._messages.keys())
        yielded_levels = buffered_levels[: len(buffered_levels) - self._size]
        for level in yielded_levels:
            yield from self._messages.pop(level)


class ContractHashes:
    def __init__(self) -> None:
        self._address_to_hashes: dict[str, tuple[int, int]] = {}
        self._hashes_to_address: dict[tuple[int, int], str] = {}

    def add(self, address: str, code_hash: int, type_hash: int) -> None:
        if address not in self._address_to_hashes:
            self._address_to_hashes[address] = (code_hash, type_hash)
        if (code_hash, type_hash) not in self._hashes_to_address:
            self._hashes_to_address[(code_hash, type_hash)] = address

    def reset(self) -> None:
        self._address_to_hashes.clear()
        self._hashes_to_address.clear()

    def get_code_hashes(self, address: str) -> tuple[int, int]:
        return self._address_to_hashes[address]

    def get_address(self, code_hash: int, type_hash: int) -> str:
        return self._hashes_to_address[(code_hash, type_hash)]


class TzktDatasource(IndexDatasource):
    _default_http_config = HTTPConfig(
        retry_sleep=1,
        retry_multiplier=1.1,
        retry_count=10,
        ratelimit_rate=100,
        ratelimit_period=1,
        connection_limit=25,
        batch_size=1000,
    )

    def __init__(
        self,
        url: str,
        http_config: HTTPConfig | None = None,
        merge_subscriptions: bool = False,
        buffer_size: int = 0,
    ) -> None:
        super().__init__(
            url=url,
            http_config=self._default_http_config.merge(http_config),
            merge_subscriptions=merge_subscriptions,
        )
        self._logger = logging.getLogger('dipdup.tzkt')
        self._buffer = MessageBuffer(buffer_size)
        self._contract_hashes = ContractHashes()

        self._ws_client: SignalRClient | None = None
        self._level: defaultdict[MessageType, int | None] = defaultdict(lambda: None)

    async def __aenter__(self) -> None:
        try:
            await super().__aenter__()

            protocol = await self.request('get', 'v1/protocols/current')
            category = 'self-hosted'
            if (instance := baking_bad.TZKT_API_URLS.get(self.url)) is not None:
                category = f'hosted ({instance})'
            self._logger.info(
                '%s, protocol v%s (%s)',
                category,
                protocol['code'],
                protocol['hash'][:8] + '…' + protocol['hash'][-6:],
            )
        except Exception as e:
            raise DatasourceError(f'Failed to connect to TzKT: {e}', self.name) from e

    @property
    def request_limit(self) -> int:
        return cast(int, self._http_config.batch_size)

    def set_logger(self, name: str) -> None:
        super().set_logger(name)
        self._buffer._logger = FormattedLogger(self._buffer._logger.name, name + ': {}')

    def get_channel_level(self, message_type: MessageType) -> int:
        """Get current level of the channel, or sync level if no messages were received yet."""
        channel_level = self._level[message_type]
        if channel_level is None:
            # NOTE: If no data messages were received since run, use sync level instead
            # NOTE: There's only one sync level for all channels, otherwise `Index.process` would fail
            channel_level = self.get_sync_level(HeadSubscription())
            if channel_level is None:
                raise FrameworkException('Neither current nor sync level is known')

        return channel_level

    def _set_channel_level(self, message_type: MessageType, level: int) -> None:
        self._level[message_type] = level

    async def get_similar_contracts(
        self,
        address: str,
        strict: bool = False,
        offset: int | None = None,
        limit: int | None = None,
    ) -> tuple[str, ...]:
        """Get addresses of contracts that share the same code hash or type hash"""
        offset, limit = offset or 0, limit or self.request_limit
        entrypoint = 'same' if strict else 'similar'
        self._logger.info('Fetching `%s` contracts for address `%s`', entrypoint, address)
        response = await self.request(
            'get',
            url=f'v1/contracts/{address}/{entrypoint}',
            params={
                'select': 'id,address',
                'offset': offset,
                'limit': limit,
            },
        )
        return tuple(item['address'] for item in response)

    async def iter_similar_contracts(
        self,
        address: str,
        strict: bool = False,
    ) -> AsyncIterator[tuple[str, ...]]:
        async for batch in self._iter_batches(self.get_similar_contracts, address, strict, cursor=False):
            yield batch

    async def get_originated_contracts(
        self,
        address: str,
        offset: int | None = None,
        limit: int | None = None,
    ) -> tuple[str, ...]:
        """Get addresses of contracts originated from given address"""
        self._logger.info('Fetching originated contracts for address `%s`', address)
        offset, limit = offset or 0, limit or self.request_limit
        response = await self.request(
            'get',
            url=f'v1/accounts/{address}/contracts',
            params={
                'select': 'id,address',
                'offset': offset,
                'limit': limit,
            },
        )
        return tuple(item['address'] for item in response)

    async def iter_originated_contracts(self, address: str) -> AsyncIterator[tuple[str, ...]]:
        async for batch in self._iter_batches(self.get_originated_contracts, address, cursor=False):
            yield batch

    async def get_contract_summary(self, address: str) -> dict[str, Any]:
        """Get contract summary"""
        self._logger.info('Fetching contract summary for address `%s`', address)
        return cast(
            dict[str, Any],
            await self.request(
                'get',
                url=f'v1/contracts/{address}',
            ),
        )

    async def get_contract_hashes(self, address: str) -> tuple[int, int]:
        """Get contract code and type hashes"""
        try:
            return self._contract_hashes.get_code_hashes(address)
        except KeyError:
            summary = await self.get_contract_summary(address)
            code_hash, type_hash = summary['codeHash'], summary['typeHash']
            self._contract_hashes.add(address, code_hash, type_hash)
            return (code_hash, type_hash)

    async def get_contract_address(self, code_hash: int, type_hash: int) -> str:
        """Get contract address by code or type hash"""
        try:
            return self._contract_hashes.get_address(code_hash, type_hash)
        except KeyError:
            response = await self.request(
                'get',
                url='v1/contracts',
                params={
                    'select': 'id,address',
                    'codeHash': code_hash,
                    'limit': 1,
                },
            )
            if not response:
                raise ValueError(f'Contract with code hash `{code_hash}` not found')
            address = cast(str, response[0]['address'])
            self._contract_hashes.add(address, code_hash, type_hash)
            return address

    async def get_contract_storage(self, address: str) -> dict[str, Any]:
        """Get contract storage"""
        self._logger.info('Fetching contract storage for address `%s`', address)
        return cast(
            dict[str, Any],
            await self.request(
                'get',
                url=f'v1/contracts/{address}/storage',
            ),
        )

    async def get_jsonschemas(self, address: str) -> dict[str, Any]:
        """Get JSONSchemas for contract's storage/parameter/bigmap types"""
        self._logger.info('Fetching jsonschemas for address `%s`', address)
        return cast(
            dict[str, Any],
            await self.request(
                'get',
                url=f'v1/contracts/{address}/interface',
            ),
        )

    async def get_big_map(
        self,
        big_map_id: int,
        level: int | None = None,
        active: bool = False,
        offset: int | None = None,
        limit: int | None = None,
    ) -> tuple[dict[str, Any], ...]:
        self._logger.info('Fetching keys of bigmap `%s`', big_map_id)
        offset, limit = offset or 0, limit or self.request_limit
        kwargs = {'active': str(active).lower()} if active else {}
        big_maps = await self.request(
            'get',
            url=f'v1/bigmaps/{big_map_id}/keys',
            params={
                **kwargs,
                'level': level,
                'offset': offset,
                'limit': limit,
            },
        )
        return tuple(big_maps)

    async def iter_big_map(
        self,
        big_map_id: int,
        level: int | None = None,
        active: bool = False,
    ) -> AsyncIterator[tuple[dict[str, Any], ...]]:
        async for batch in self._iter_batches(
            self.get_big_map,
            big_map_id,
            level,
            active,
            cursor=False,
        ):
            yield batch

    async def get_contract_big_maps(
        self,
        address: str,
        offset: int | None = None,
        limit: int | None = None,
    ) -> tuple[dict[str, Any], ...]:
        offset, limit = offset or 0, limit or self.request_limit
        big_maps = await self.request(
            'get',
            url=f'v1/contracts/{address}/bigmaps',
            params={
                'offset': offset,
                'limit': limit,
            },
        )
        return tuple(big_maps)

    async def iter_contract_big_maps(
        self,
        address: str,
    ) -> AsyncIterator[tuple[dict[str, Any], ...]]:
        async for batch in self._iter_batches(self.get_contract_big_maps, address, cursor=False):
            yield batch

    async def get_head_block(self) -> HeadBlockData:
        """Get latest block (head)"""
        self._logger.info('Fetching latest block')
        head_block_json = await self.request(
            'get',
            url='v1/head',
        )
        return self.convert_head_block(head_block_json)

    async def get_block(self, level: int) -> BlockData:
        """Get block by level"""
        self._logger.info('Fetching block %s', level)
        block_json = await self.request(
            'get',
            url=f'v1/blocks/{level}',
        )
        return self.convert_block(block_json)

    async def get_migration_originations(
        self,
        first_level: int = 0,
        offset: int | None = None,
        limit: int | None = None,
    ) -> tuple[OperationData, ...]:
        """Get contracts originated from migrations"""
        offset, limit = offset or 0, limit or self.request_limit
        self._logger.info('Fetching contracts originated with migrations')
        raw_migrations = await self.request(
            'get',
            url='v1/operations/migrations',
            params={
                'kind': 'origination',
                'level.ge': first_level,
                'select': ','.join(ORIGINATION_MIGRATION_FIELDS),
                'offset.cr': offset,
                'limit': limit,
            },
        )
        return tuple(self.convert_migration_origination(m) for m in raw_migrations)

    async def iter_migration_originations(
        self,
        first_level: int = 0,
    ) -> AsyncIterator[tuple[OperationData, ...]]:
        async for batch in self._iter_batches(
            self.get_migration_originations,
            first_level,
        ):
            yield batch

    async def get_originations(
        self,
        addresses: set[str] | None = None,
        code_hashes: set[int] | None = None,
        first_level: int | None = None,
        last_level: int | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> tuple[OperationData, ...]:
        offset, limit = offset or 0, limit or self.request_limit
        raw_originations: list[dict[str, Any]] = []
        params = self._get_request_params(
            first_level=first_level,
            last_level=last_level,
            offset=offset,
            limit=limit,
            select=ORIGINATION_OPERATION_FIELDS,
            status='applied',
            cursor=bool(code_hashes),
        )

        # NOTE: TzKT may hit URL length limit with hundreds of originations in a single request.
        # NOTE: Chunk of 100 addresses seems like a reasonable choice - URL of ~4000 characters.
        # NOTE: Other operation requests won't hit that limit.
        if addresses and not code_hashes:
            # FIXME: No pagination because of URL length limit workaround
            for addresses_chunk in split_by_chunks(list(addresses), ORIGINATION_REQUEST_LIMIT):
                raw_originations += await self.request(
                    'get',
                    url='v1/operations/originations',
                    params={
                        **params,
                        'originatedContract.in': ','.join(addresses_chunk),
                    },
                )
        elif code_hashes and not addresses:
            raw_originations += await self.request(
                'get',
                url='v1/operations/originations',
                params={
                    **params,
                    # FIXME: Need a helper for this join
                    'codeHash.in': ','.join(str(h) for h in code_hashes),
                },
            )
        else:
            raise FrameworkException('Either `addresses` or `code_hashes` should be specified')

        # NOTE: `type` field needs to be set manually when requesting operations by specific type
        return tuple(self.convert_operation(op, type_='origination') for op in raw_originations)

    def _get_request_params(
        self,
        first_level: int | None = None,
        last_level: int | None = None,
        offset: int | None = None,
        limit: int | None = None,
        select: Sequence[str | int] | None = None,
        cursor: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            'limit': limit or self.request_limit,
        }
        if first_level:
            params['level.ge'] = first_level
        if last_level:
            params['level.le'] = last_level
        if offset:
            if cursor:
                params['offset.cr'] = offset
            else:
                params['offset'] = offset
        if select:
            params['select'] = ','.join(str(a) for a in select)
        return {
            **params,
            **kwargs,
        }

    async def get_transactions(
        self,
        field: str,
        addresses: set[str] | None,
        code_hashes: set[int] | None,
        first_level: int | None = None,
        last_level: int | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> tuple[OperationData, ...]:
        params = self._get_request_params(
            first_level,
            last_level,
            offset,
            limit,
            TRANSACTION_OPERATION_FIELDS,
            cursor=True,
            status='applied',
        )
        if addresses and not code_hashes:
            params[f'{field}.in'] = ','.join(addresses)
        elif code_hashes and not addresses:
            params[f'{field}CodeHash.in'] = ','.join(str(h) for h in code_hashes)

        raw_transactions = await self.request(
            'get',
            url='v1/operations/transactions',
            params=params,
        )

        # NOTE: `type` field needs to be set manually when requesting operations by specific type
        return tuple(self.convert_operation(op, type_='transaction') for op in raw_transactions)

    async def iter_transactions(
        self,
        field: str,
        addresses: set[str],
        first_level: int,
        last_level: int,
    ) -> AsyncIterator[tuple[OperationData, ...]]:
        async for batch in self._iter_batches(
            self.get_transactions,
            field,
            addresses,
            first_level,
            last_level,
        ):
            yield batch

    async def get_big_maps(
        self,
        addresses: set[str],
        paths: set[str],
        first_level: int,
        last_level: int,
        offset: int | None = None,
        limit: int | None = None,
    ) -> tuple[BigMapData, ...]:
        offset, limit = offset or 0, limit or self.request_limit
        raw_big_maps = await self.request(
            'get',
            url='v1/bigmaps/updates',
            params={
                'contract.in': ','.join(addresses),
                'path.in': ','.join(paths),
                'level.ge': first_level,
                'level.le': last_level,
                'offset': offset,
                'limit': limit,
            },
        )
        return tuple(self.convert_big_map(bm) for bm in raw_big_maps)

    async def iter_big_maps(
        self,
        addresses: set[str],
        paths: set[str],
        first_level: int,
        last_level: int,
    ) -> AsyncIterator[tuple[BigMapData, ...]]:
        async for batch in self._iter_batches(
            self.get_big_maps,
            addresses,
            paths,
            first_level,
            last_level,
            cursor=False,
        ):
            yield batch

    async def get_quote(self, level: int) -> QuoteData:
        """Get quote for block"""
        self._logger.info('Fetching quotes for level %s', level)
        quote_json = await self.request(
            'get',
            url='v1/quotes',
            params={'level': level},
        )
        return self.convert_quote(quote_json[0])

    async def get_quotes(
        self,
        first_level: int,
        last_level: int,
        offset: int | None = None,
        limit: int | None = None,
    ) -> tuple[QuoteData, ...]:
        """Get quotes for blocks"""
        offset, limit = offset or 0, limit or self.request_limit
        self._logger.info('Fetching quotes for levels %s-%s', first_level, last_level)
        quotes_json = await self.request(
            'get',
            url='v1/quotes',
            params={
                'level.ge': first_level,
                'level.le': last_level,
                'offset.cr': offset,
                'limit': limit,
            },
        )
        return tuple(self.convert_quote(quote) for quote in quotes_json)

    async def iter_quotes(
        self,
        first_level: int,
        last_level: int,
    ) -> AsyncIterator[tuple[QuoteData, ...]]:
        """Iterate quotes for blocks"""
        async for batch in self._iter_batches(
            self.get_quotes,
            first_level,
            last_level,
        ):
            yield batch

    async def get_token_transfers(
        self,
        token_addresses: set[str],
        token_ids: set[int],
        from_addresses: set[str],
        to_addresses: set[str],
        first_level: int,
        last_level: int,
        offset: int | None = None,
        limit: int | None = None,
    ) -> tuple[TokenTransferData, ...]:
        """Get token transfers for contract"""
        offset, limit = offset or 0, limit or self.request_limit

        raw_token_transfers = await self.request(
            'get',
            url='v1/tokens/transfers',
            params={
                'token.contract.in': ','.join(token_addresses),
                'token.id.in': ','.join(str(token_id) for token_id in token_ids),
                'from.in': ','.join(from_addresses),
                'to.in': ','.join(to_addresses),
                'level.ge': first_level,
                'level.le': last_level,
                'offset': offset,
                'limit': limit,
            },
        )
        return tuple(self.convert_token_transfer(item) for item in raw_token_transfers)

    async def iter_token_transfers(
        self,
        token_addresses: set[str],
        token_ids: set[int],
        from_addresses: set[str],
        to_addresses: set[str],
        first_level: int,
        last_level: int,
    ) -> AsyncIterator[tuple[TokenTransferData, ...]]:
        """Iterate token transfers for contract"""
        async for batch in self._iter_batches(
            self.get_token_transfers,
            token_addresses,
            token_ids,
            from_addresses,
            to_addresses,
            first_level,
            last_level,
            cursor=False,
        ):
            yield batch

    async def get_events(
        self,
        addresses: set[str],
        tags: set[str],
        first_level: int,
        last_level: int,
        offset: int | None = None,
        limit: int | None = None,
    ) -> tuple[EventData, ...]:
        offset, limit = offset or 0, limit or self.request_limit
        raw_events = await self.request(
            'get',
            url='v1/contracts/events',
            params={
                'contract.in': ','.join(addresses),
                'tag.in': ','.join(tags),
                'level.ge': first_level,
                'level.le': last_level,
                # TODO: Cursor supported?
                'offset': offset,
                'limit': limit,
            },
        )
        return tuple(self.convert_event(e) for e in raw_events)

    async def iter_events(
        self,
        addresses: set[str],
        tags: set[str],
        first_level: int,
        last_level: int,
    ) -> AsyncIterator[tuple[EventData, ...]]:
        async for batch in self._iter_batches(
            self.get_events,
            addresses,
            tags,
            first_level,
            last_level,
            cursor=False,
        ):
            yield batch

    async def add_index(self, index_config: ResolvedIndexConfigU) -> None:
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
        method = subscription.method
        request: list[dict[str, Any]] = subscription.get_request()

        event = Event()

        async def _on_subscribe(message: CompletionMessage) -> None:
            if message.error:
                await self._on_error(message)
            level = cast(int, message.result)
            self._subscriptions.set_sync_level(subscription, level)
            event.set()

        await self._send(method, request, _on_subscribe)
        await event.wait()

    async def _iter_batches(
        self, fn: Callable[..., Awaitable[Sequence[Any]]], *args: Any, cursor: bool = True, **kwargs: Any
    ) -> AsyncIterator[Any]:
        if set(kwargs).intersection(('offset', 'offset.cr', 'limit')):
            raise ValueError('`offset` and `limit` arguments are not allowed')

        size, offset = self.request_limit, 0
        while size == self.request_limit:
            result = await fn(*args, offset=offset, **kwargs)
            if not result:
                return

            yield result

            size = len(result)
            if cursor:
                # NOTE: Guess if response is already deserialized or not
                try:
                    offset = result[-1]['id']
                except TypeError:
                    offset = result[-1].id
            else:
                offset += self.request_limit

    def _get_ws_client(self) -> SignalRClient:
        """Create SignalR client, register message callbacks"""
        if self._ws_client:
            return self._ws_client

        self._logger.info('Creating websocket client')
        self._ws_client = SignalRClient(
            url=f'{self._http._url}/v1/events',
            max_size=None,
        )

        self._ws_client.on_open(self._on_connected)
        self._ws_client.on_close(self._on_disconnected)
        self._ws_client.on_error(self._on_error)

        self._ws_client.on('operations', partial(self._on_message, MessageType.operation))
        self._ws_client.on('transfers', partial(self._on_message, MessageType.token_transfer))
        self._ws_client.on('bigmaps', partial(self._on_message, MessageType.big_map))
        self._ws_client.on('head', partial(self._on_message, MessageType.head))
        self._ws_client.on('events', partial(self._on_message, MessageType.event))

        return self._ws_client

    async def run(self) -> None:
        self._logger.info('Establishing realtime connection')
        ws = self._get_ws_client()

        async def _wrapper() -> None:
            # FIXME: These defaults should be somewhere else
            retry_sleep = self._http_config.retry_sleep or 0
            retry_multiplier = self._http_config.retry_multiplier or 1
            retry_count = self._http_config.retry_count or sys.maxsize

            for _ in range(retry_count):
                try:
                    await ws.run()
                except WebsocketConnectionError as e:
                    self._logger.error('Websocket connection error: %s', e)
                    await self.emit_disconnected()
                    await asyncio.sleep(retry_sleep)
                    retry_sleep *= retry_multiplier

        await create_task(_wrapper())

    async def _on_connected(self) -> None:
        self._logger.info('Realtime connection established')
        # NOTE: Subscribing here will block WebSocket loop, don't do it.
        await self.emit_connected()

    async def _on_disconnected(self) -> None:
        self._logger.info('Realtime connection lost, resetting subscriptions')
        self._subscriptions.reset()
        # NOTE: Just in case
        self._contract_hashes.reset()
        await self.emit_disconnected()

    async def _on_error(self, message: CompletionMessage) -> NoReturn:
        """Raise exception from WS server's error message"""
        raise DatasourceError(datasource=self.name, msg=cast(str, message.error))

    async def _on_message(self, type_: MessageType, message: list[dict[str, Any]]) -> None:
        """Parse message received from Websocket, ensure it's correct in the current context and yield data."""
        # NOTE: Parse messages and either buffer or yield data
        for item in message:
            tzkt_type = TzktMessageType(item['type'])
            # NOTE: Legacy, sync level returned by TzKT during negotiation
            if tzkt_type == TzktMessageType.STATE:
                continue

            message_level = item['state']
            channel_level = self.get_channel_level(type_)
            self._set_channel_level(type_, message_level)

            self._logger.info(
                'Realtime message received: %s, %s, %s -> %s',
                type_.value,
                tzkt_type.name,
                channel_level,
                message_level,
            )

            # NOTE: Put data messages to buffer by level
            if tzkt_type == TzktMessageType.DATA:
                self._buffer.add(type_, message_level, item['data'])

            # NOTE: Try to process rollback automatically, emit if failed
            elif tzkt_type == TzktMessageType.REORG:
                if self._buffer.rollback(type_, channel_level, message_level):
                    self._logger.info('Rolled back blocks were dropped from realtime message buffer')
                else:
                    self._logger.info('Rolled back blocks are not buffered; proceeding to database rollback')
                    await self.emit_rollback(type_, channel_level, message_level)

            else:
                raise NotImplementedError(f'Unknown message type: {tzkt_type}')

        # NOTE: Process extensive data from buffer
        for buffered_message in self._buffer.yield_from():
            if buffered_message.type == MessageType.operation:
                await self._process_operations_data(cast(list[dict[str, Any]], buffered_message.data))
            elif buffered_message.type == MessageType.token_transfer:
                await self._process_token_transfers_data(cast(list[dict[str, Any]], buffered_message.data))
            elif buffered_message.type == MessageType.big_map:
                await self._process_big_maps_data(cast(list[dict[str, Any]], buffered_message.data))
            elif buffered_message.type == MessageType.head:
                await self._process_head_data(cast(dict[str, Any], buffered_message.data))
            elif buffered_message.type == MessageType.event:
                await self._process_events_data(cast(list[dict[str, Any]], buffered_message.data))
            else:
                raise NotImplementedError(f'Unknown message type: {buffered_message.type}')

    async def _process_operations_data(self, data: list[dict[str, Any]]) -> None:
        """Parse and emit raw operations from WS"""
        level_operations: defaultdict[int, deque[OperationData]] = defaultdict(deque)

        for operation_json in data:
            if operation_json['status'] != 'applied':
                continue
            operation = self.convert_operation(operation_json)
            level_operations[operation.level].append(operation)

        for _level, operations in level_operations.items():
            await self.emit_operations(tuple(operations))

    async def _process_token_transfers_data(self, data: list[dict[str, Any]]) -> None:
        """Parse and emit raw token transfers from WS"""
        level_token_transfers: defaultdict[int, deque[TokenTransferData]] = defaultdict(deque)

        for token_transfer_json in data:
            token_transfer = self.convert_token_transfer(token_transfer_json)
            level_token_transfers[token_transfer.level].append(token_transfer)

        for _level, token_transfers in level_token_transfers.items():
            await self.emit_token_transfers(tuple(token_transfers))

    async def _process_big_maps_data(self, data: list[dict[str, Any]]) -> None:
        """Parse and emit raw big map diffs from WS"""
        level_big_maps: defaultdict[int, deque[BigMapData]] = defaultdict(deque)

        big_maps: deque[BigMapData] = deque()
        for big_map_json in data:
            big_map = self.convert_big_map(big_map_json)
            level_big_maps[big_map.level].append(big_map)

        for _level, big_maps in level_big_maps.items():
            await self.emit_big_maps(tuple(big_maps))

    async def _process_head_data(self, data: dict[str, Any]) -> None:
        """Parse and emit raw head block from WS"""
        block = self.convert_head_block(data)
        await self.emit_head(block)

    async def _process_events_data(self, data: list[dict[str, Any]]) -> None:
        """Parse and emit raw big map diffs from WS"""
        level_events: defaultdict[int, deque[EventData]] = defaultdict(deque)

        events: deque[EventData] = deque()
        for event_json in data:
            event = self.convert_event(event_json)
            level_events[event.level].append(event)

        for _level, events in level_events.items():
            await self.emit_events(tuple(events))

    @classmethod
    def convert_operation(
        cls,
        operation_json: dict[str, Any],
        type_: str | None = None,
    ) -> OperationData:
        """Convert raw operation message from WS/REST into dataclass"""
        # NOTE: Migration originations are handled in a separate method
        sender_json = operation_json.get('sender') or {}
        target_json = operation_json.get('target') or {}
        initiator_json = operation_json.get('initiator') or {}
        delegate_json = operation_json.get('delegate') or {}
        parameter_json = operation_json.get('parameter') or {}
        originated_contract_json = operation_json.get('originatedContract') or {}

        if (amount := operation_json.get('contractBalance')) is None:
            amount = operation_json.get('amount')

        entrypoint, parameter = parameter_json.get('entrypoint'), parameter_json.get('value')
        if target_json.get('address', '').startswith('KT1'):
            # NOTE: TzKT returns None for `default` entrypoint
            if entrypoint is None:
                entrypoint = 'default'

                # NOTE: Empty parameter in this case means `{"prim": "Unit"}`
                if parameter is None:
                    parameter = {}

        return OperationData(
            type=type_ or operation_json['type'],
            id=operation_json['id'],
            level=operation_json['level'],
            timestamp=cls._parse_timestamp(operation_json['timestamp']),
            block=operation_json.get('block'),
            hash=operation_json['hash'],
            counter=operation_json['counter'],
            sender_address=sender_json.get('address'),
            sender_code_hash=operation_json.get('senderCodeHash'),
            target_address=target_json.get('address'),
            target_code_hash=operation_json.get('targetCodeHash'),
            initiator_address=initiator_json.get('address'),
            amount=amount,
            status=operation_json['status'],
            has_internals=operation_json.get('hasInternals'),
            sender_alias=operation_json['sender'].get('alias'),
            nonce=operation_json.get('nonce'),
            target_alias=target_json.get('alias'),
            initiator_alias=initiator_json.get('alias'),
            entrypoint=entrypoint,
            parameter_json=parameter,
            originated_contract_address=originated_contract_json.get('address'),
            originated_contract_alias=originated_contract_json.get('alias'),
            originated_contract_type_hash=originated_contract_json.get('typeHash'),
            originated_contract_code_hash=originated_contract_json.get('codeHash'),
            originated_contract_tzips=originated_contract_json.get('tzips'),
            storage=operation_json.get('storage'),
            diffs=operation_json.get('diffs') or (),
            delegate_address=delegate_json.get('address'),
            delegate_alias=delegate_json.get('alias'),
        )

    @classmethod
    def convert_migration_origination(
        cls,
        migration_origination_json: dict[str, Any],
    ) -> OperationData:
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
            sender_code_hash=None,
            target_address=None,
            target_code_hash=None,
            initiator_address=None,
        )

    @classmethod
    def convert_big_map(
        cls,
        big_map_json: dict[str, Any],
    ) -> BigMapData:
        """Convert raw big map diff message from WS/REST into dataclass"""
        action = BigMapAction(big_map_json['action'])
        active = action not in (BigMapAction.REMOVE, BigMapAction.REMOVE_KEY)
        return BigMapData(
            id=big_map_json['id'],
            level=big_map_json['level'],
            # NOTE: missing `operation_id` field in API to identify operation
            operation_id=big_map_json['level'],
            timestamp=cls._parse_timestamp(big_map_json['timestamp']),
            bigmap=big_map_json['bigmap'],
            contract_address=big_map_json['contract']['address'],
            path=big_map_json['path'],
            action=action,
            active=active,
            key=big_map_json.get('content', {}).get('key'),
            value=big_map_json.get('content', {}).get('value'),
        )

    @classmethod
    def convert_block(
        cls,
        block_json: dict[str, Any],
    ) -> BlockData:
        """Convert raw block message from REST into dataclass"""
        return BlockData(
            level=block_json['level'],
            hash=block_json['hash'],
            timestamp=cls._parse_timestamp(block_json['timestamp']),
            proto=block_json['proto'],
            priority=block_json.get('priority'),
            validations=block_json['validations'],
            deposit=block_json['deposit'],
            reward=block_json['reward'],
            fees=block_json['fees'],
            nonce_revealed=block_json['nonceRevealed'],
            baker_address=block_json.get('baker', {}).get('address'),
            baker_alias=block_json.get('baker', {}).get('alias'),
        )

    @classmethod
    def convert_head_block(
        cls,
        head_block_json: dict[str, Any],
    ) -> HeadBlockData:
        """Convert raw head block message from WS/REST into dataclass"""
        return HeadBlockData(
            chain=head_block_json['chain'],
            chain_id=head_block_json['chainId'],
            cycle=head_block_json['cycle'],
            level=head_block_json['level'],
            hash=head_block_json['hash'],
            protocol=head_block_json['protocol'],
            next_protocol=head_block_json['nextProtocol'],
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
            quote_gbp=Decimal(head_block_json['quoteGbp']),
        )

    @classmethod
    def convert_quote(cls, quote_json: dict[str, Any]) -> QuoteData:
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
            gbp=Decimal(quote_json['gbp']),
        )

    @classmethod
    def convert_token_transfer(cls, token_transfer_json: dict[str, Any]) -> TokenTransferData:
        """Convert raw token transfer message from REST or WS into dataclass"""
        token_json = token_transfer_json.get('token') or {}
        contract_json = token_json.get('contract') or {}
        from_json = token_transfer_json.get('from') or {}
        to_json = token_transfer_json.get('to') or {}
        standard = token_json.get('standard')
        metadata = token_json.get('metadata')
        return TokenTransferData(
            id=token_transfer_json['id'],
            level=token_transfer_json['level'],
            timestamp=cls._parse_timestamp(token_transfer_json['timestamp']),
            tzkt_token_id=token_json['id'],
            contract_address=contract_json.get('address'),
            contract_alias=contract_json.get('alias'),
            token_id=token_json.get('tokenId'),
            standard=TokenStandard(standard) if standard else None,
            metadata=metadata if isinstance(metadata, dict) else {},
            from_alias=from_json.get('alias'),
            from_address=from_json.get('address'),
            to_alias=to_json.get('alias'),
            to_address=to_json.get('address'),
            amount=token_transfer_json.get('amount'),
            tzkt_transaction_id=token_transfer_json.get('transactionId'),
            tzkt_origination_id=token_transfer_json.get('originationId'),
            tzkt_migration_id=token_transfer_json.get('migrationId'),
        )

    @classmethod
    def convert_event(cls, event_json: dict[str, Any]) -> EventData:
        """Convert raw event message from WS/REST into dataclass"""
        return EventData(
            id=event_json['id'],
            level=event_json['level'],
            timestamp=cls._parse_timestamp(event_json['timestamp']),
            tag=event_json['tag'],
            payload=event_json.get('payload'),
            contract_address=event_json['contract']['address'],
            contract_alias=event_json['contract'].get('alias'),
            contract_code_hash=event_json['codeHash'],
            transaction_id=event_json.get('transactionId'),
        )

    async def _send(
        self,
        method: str,
        arguments: list[dict[str, Any]],
        on_invocation: Callable[[CompletionMessage], Awaitable[None]] | None = None,
    ) -> None:
        client = self._get_ws_client()
        await client.send(method, arguments, on_invocation)

    @classmethod
    def _parse_timestamp(cls, timestamp: str) -> datetime:
        return datetime.fromisoformat(timestamp[:-1]).replace(tzinfo=timezone.utc)
