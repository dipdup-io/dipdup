import asyncio
import logging
from asyncio import Event
from collections import defaultdict
from collections import deque
from dataclasses import fields
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

import pysignalr.exceptions
from pysignalr.client import SignalRClient
from pysignalr.messages import CompletionMessage

from dipdup.config import HttpConfig
from dipdup.config.tezos_tzkt import TZKT_API_URLS
from dipdup.config.tezos_tzkt import TzktDatasourceConfig
from dipdup.datasources import IndexDatasource
from dipdup.exceptions import DatasourceError
from dipdup.exceptions import FrameworkException
from dipdup.models import Head
from dipdup.models import MessageType
from dipdup.models.tezos_tzkt import HeadSubscription
from dipdup.models.tezos_tzkt import TzktBigMapData
from dipdup.models.tezos_tzkt import TzktBlockData
from dipdup.models.tezos_tzkt import TzktEventData
from dipdup.models.tezos_tzkt import TzktHeadBlockData
from dipdup.models.tezos_tzkt import TzktMessageType
from dipdup.models.tezos_tzkt import TzktOperationData
from dipdup.models.tezos_tzkt import TzktQuoteData
from dipdup.models.tezos_tzkt import TzktSubscription
from dipdup.models.tezos_tzkt import TzktTokenTransferData
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
BIGMAP_FIELDS = (
    'ptr',
    'contract',
    'path',
    'tags',
    'active',
    'firstLevel',
    'lastLevel',
    'totalKeys',
    'activeKeys',
    'updates',
    'keyType',
    'valueType',
)
TZKT_TOKEN_TRANSFER_DATA_FIELDS = (
    'token',
    'from',
    'to',
    'id',
    'level',
    'timestamp',
    'amount',
    'transactionId',
    'originationId',
    'migrationId',
)


EmptyCallback = Callable[[], Awaitable[None]]
HeadCallback = Callable[['TzktDatasource', TzktHeadBlockData], Awaitable[None]]
OperationsCallback = Callable[['TzktDatasource', tuple[TzktOperationData, ...]], Awaitable[None]]
TokenTransfersCallback = Callable[['TzktDatasource', tuple[TzktTokenTransferData, ...]], Awaitable[None]]
BigMapsCallback = Callable[['TzktDatasource', tuple[TzktBigMapData, ...]], Awaitable[None]]
EventsCallback = Callable[['TzktDatasource', tuple[TzktEventData, ...]], Awaitable[None]]
# TODO: move somewhere
RollbackCallback = Callable[['IndexDatasource', MessageType, int, int], Awaitable[None]]


class TzktMessageAction(Enum):
    STATE = 0
    DATA = 1
    REORG = 2


MessageData = dict[str, Any] | list[dict[str, Any]]


class BufferedMessage(NamedTuple):
    type: TzktMessageType
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

    def add(self, type_: TzktMessageType, level: int, data: MessageData) -> None:
        """Add a message to the buffer."""
        if level not in self._messages:
            self._messages[level] = []
        self._messages[level].append(BufferedMessage(type_, data))

    def rollback(self, type_: TzktMessageType, channel_level: int, message_level: int) -> bool:
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
    """Contract hashes cache"""

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


class TzktDatasource(IndexDatasource[TzktDatasourceConfig]):
    _default_http_config = HttpConfig(
        retry_sleep=1,
        retry_multiplier=1.1,
        retry_count=10,
        ratelimit_rate=100,
        ratelimit_period=1,
        connection_limit=25,
        batch_size=10_000,
    )

    def __init__(
        self,
        config: TzktDatasourceConfig,
    ) -> None:
        super().__init__(config)
        self._logger = logging.getLogger('dipdup.tzkt')
        self._buffer = MessageBuffer(config.buffer_size)
        self._contract_hashes = ContractHashes()

        self._on_connected_callbacks: set[EmptyCallback] = set()
        self._on_disconnected_callbacks: set[EmptyCallback] = set()
        self._on_head_callbacks: set[HeadCallback] = set()
        self._on_operations_callbacks: set[OperationsCallback] = set()
        self._on_token_transfers_callbacks: set[TokenTransfersCallback] = set()
        self._on_big_maps_callbacks: set[BigMapsCallback] = set()
        self._on_events_callbacks: set[EventsCallback] = set()
        self._on_rollback_callbacks: set[RollbackCallback] = set()
        self._network: str | None = None

        self._signalr_client: SignalRClient | None = None
        self._channel_levels: defaultdict[TzktMessageType, int | None] = defaultdict(lambda: None)

    async def __aenter__(self) -> None:
        try:
            await super().__aenter__()

            protocol = await self.request('get', 'v1/protocols/current')
            category = 'self-hosted'
            if (instance := TZKT_API_URLS.get(self.url)) is not None:
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
    def network(self) -> str:
        if not self._network:
            raise FrameworkException('Network is not set')
        return self._network

    @property
    def request_limit(self) -> int:
        return self._http_config.batch_size

    # FIXME: Join retry logic with other index datasources
    async def run(self) -> None:
        self._logger.info('Establishing realtime connection')
        signalr_client = self._get_signalr_client()
        retry_sleep = self._http_config.retry_sleep

        for _ in range(1, self._http_config.retry_count + 1):
            try:
                await signalr_client.run()
            except pysignalr.exceptions.ConnectionError as e:
                self._logger.error('Websocket connection error: %s', e)
                await self.emit_disconnected()
                await asyncio.sleep(retry_sleep)
                retry_sleep *= self._http_config.retry_multiplier

        raise DatasourceError('Websocket connection failed', self.name)

    async def initialize(self) -> None:
        head_block = await self.get_head_block()
        self.set_network(head_block.chain)
        self.set_sync_level(
            subscription=None,
            level=head_block.level,
        )

        db_head = await Head.filter(name=self.name).first()
        if not db_head:
            return

        # FIXME: No ctx to throw reorg; VERY IMPORTANT CHECK
        # NOTE: Ensure that no reorgs happened while we were offline
        # actual_head = await self.get_block(db_head.level)
        # if db_head.hash != actual_head.hash:
        #     await self._ctx.reindex(
        #         ReindexingReason.rollback,
        #         datasource=self.name,
        #         level=db_head.level,
        #         stored_block_hash=db_head.hash,
        #         actual_block_hash=actual_head.hash,
        #     )

    def call_on_head(self, fn: HeadCallback) -> None:
        self._on_head_callbacks.add(fn)

    def call_on_operations(self, fn: OperationsCallback) -> None:
        self._on_operations_callbacks.add(fn)

    def call_on_token_transfers(self, fn: TokenTransfersCallback) -> None:
        self._on_token_transfers_callbacks.add(fn)

    def call_on_big_maps(self, fn: BigMapsCallback) -> None:
        self._on_big_maps_callbacks.add(fn)

    def call_on_events(self, fn: EventsCallback) -> None:
        self._on_events_callbacks.add(fn)

    def call_on_rollback(self, fn: RollbackCallback) -> None:
        self._on_rollback_callbacks.add(fn)

    def call_on_connected(self, fn: EmptyCallback) -> None:
        self._on_connected_callbacks.add(fn)

    def call_on_disconnected(self, fn: EmptyCallback) -> None:
        self._on_disconnected_callbacks.add(fn)

    async def emit_head(self, head: TzktHeadBlockData) -> None:
        for fn in self._on_head_callbacks:
            await fn(self, head)

    async def emit_operations(self, operations: tuple[TzktOperationData, ...]) -> None:
        for fn in self._on_operations_callbacks:
            await fn(self, operations)

    async def emit_token_transfers(self, token_transfers: tuple[TzktTokenTransferData, ...]) -> None:
        for fn in self._on_token_transfers_callbacks:
            await fn(self, token_transfers)

    async def emit_big_maps(self, big_maps: tuple[TzktBigMapData, ...]) -> None:
        for fn in self._on_big_maps_callbacks:
            await fn(self, big_maps)

    async def emit_events(self, events: tuple[TzktEventData, ...]) -> None:
        for fn in self._on_events_callbacks:
            await fn(self, events)

    async def emit_rollback(self, type_: MessageType, from_level: int, to_level: int) -> None:
        for fn in self._on_rollback_callbacks:
            await fn(self, type_, from_level, to_level)

    async def emit_connected(self) -> None:
        for fn in self._on_connected_callbacks:
            await fn()

    async def emit_disconnected(self) -> None:
        for fn in self._on_disconnected_callbacks:
            await fn()

    def set_network(self, network: str) -> None:
        if self._network:
            raise FrameworkException('Network is already set')
        self._network = network

    def set_logger(self, name: str) -> None:
        super().set_logger(name)
        self._buffer._logger = FormattedLogger(self._buffer._logger.name, name + ': {}')

    def get_channel_level(self, message_type: TzktMessageType) -> int:
        """Get current level of the channel, or sync level if no messages were received yet."""
        channel_level = self._channel_levels[message_type]
        if channel_level is None:
            # NOTE: If no data messages were received since run, use sync level instead
            # NOTE: There's only one sync level for all channels, otherwise `Index.process` would fail
            channel_level = self.get_sync_level(HeadSubscription())
            if channel_level is None:
                raise FrameworkException('Neither current nor sync level is known')

        return channel_level

    async def get_similar_contracts(
        self,
        address: str,
        strict: bool = False,
        offset: int | None = None,
        limit: int | None = None,
    ) -> tuple[dict[str, str], ...]:
        """Get addresses of contracts that share the same code hash or type hash"""
        entrypoint = 'same' if strict else 'similar'
        self._logger.info('Fetching `%s` contracts for address `%s`', entrypoint, address)

        params = self._get_request_params(
            offset=offset,
            limit=limit,
            select=(
                'id',
                'address',
            ),
            values=True,
            cursor=True,
        )
        return await self._request_values_dict(
            'get',
            url=f'v1/contracts/{address}/{entrypoint}',
            params=params,
        )

    async def iter_similar_contracts(
        self,
        address: str,
        strict: bool = False,
    ) -> AsyncIterator[tuple[dict[str, str], ...]]:
        async for batch in self._iter_batches(
            self.get_similar_contracts,
            address,
            strict,
            cursor=True,
        ):
            yield batch

    async def get_originated_contracts(
        self,
        address: str,
        offset: int | None = None,
        limit: int | None = None,
    ) -> tuple[dict[str, str], ...]:
        """Get addresses of contracts originated from given address"""
        self._logger.info('Fetching originated contracts for address `%s`', address)
        params = self._get_request_params(
            offset=offset,
            limit=limit,
            select=(
                'id',
                'address',
            ),
            values=True,
            cursor=True,
        )
        return await self._request_values_dict(
            'get',
            url='v1/contracts',
            params={
                'creator.eq': address,
                **params,
            },
        )

    async def iter_originated_contracts(self, address: str) -> AsyncIterator[tuple[dict[str, str], ...]]:
        async for batch in self._iter_batches(
            self.get_originated_contracts,
            address,
            cursor=True,
        ):
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
                raise ValueError(f'Contract with code hash `{code_hash}` not found') from None
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
        params = self._get_request_params(
            offset=offset,
            limit=limit,
        )
        if level:
            params['level'] = level
        if active:
            params['active'] = 'true'

        big_maps = await self.request(
            'get',
            url=f'v1/bigmaps/{big_map_id}/keys',
            params=params,
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
        params = self._get_request_params(
            offset=offset,
            limit=limit,
            select=BIGMAP_FIELDS,
            values=True,
        )
        return await self._request_values_dict(
            'get',
            url=f'v1/contracts/{address}/bigmaps',
            params=params,
        )

    async def iter_contract_big_maps(
        self,
        address: str,
    ) -> AsyncIterator[tuple[dict[str, Any], ...]]:
        async for batch in self._iter_batches(
            self.get_contract_big_maps,
            address,
            cursor=False,
        ):
            yield batch

    async def get_head_block(self) -> TzktHeadBlockData:
        """Get latest block (head)"""
        self._logger.info('Fetching latest block')
        head_block_json = await self.request(
            'get',
            url='v1/head',
        )
        return TzktHeadBlockData.from_json(head_block_json)

    async def get_block(self, level: int) -> TzktBlockData:
        """Get block by level"""
        self._logger.info('Fetching block %s', level)
        block_json = await self.request(
            'get',
            url=f'v1/blocks/{level}',
        )
        return TzktBlockData.from_json(block_json)

    async def get_migration_originations(
        self,
        first_level: int | None = None,
        last_level: int | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> tuple[TzktOperationData, ...]:
        """Get contracts originated from migrations"""
        self._logger.info('Fetching contracts originated with migrations')
        params = self._get_request_params(
            first_level=first_level,
            last_level=last_level,
            offset=offset,
            limit=limit,
            select=ORIGINATION_MIGRATION_FIELDS,
            values=True,
            cursor=True,
            kind='origination',
        )
        raw_migrations = await self._request_values_dict(
            'get',
            url='v1/operations/migrations',
            params=params,
        )
        return tuple(TzktOperationData.from_migration_json(m) for m in raw_migrations)

    async def iter_migration_originations(
        self,
        first_level: int | None = None,
        last_level: int | None = None,
    ) -> AsyncIterator[tuple[TzktOperationData, ...]]:
        async for batch in self._iter_batches(
            self.get_migration_originations,
            first_level,
            last_level,
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
    ) -> tuple[TzktOperationData, ...]:
        offset, limit = offset or 0, limit or self.request_limit
        raw_originations: list[dict[str, Any]] = []
        params = self._get_request_params(
            first_level=first_level,
            last_level=last_level,
            offset=offset,
            limit=limit,
            select=ORIGINATION_OPERATION_FIELDS,
            values=True,
            status='applied',
            cursor=bool(code_hashes) or bool(not code_hashes and not addresses),
        )

        # NOTE: TzKT may hit URL length limit with hundreds of originations in a single request.
        # NOTE: Chunk of 100 addresses seems like a reasonable choice - URL of ~4000 characters.
        # NOTE: Other operation requests won't hit that limit.
        if addresses and not code_hashes:
            # FIXME: No pagination because of URL length limit workaround
            for addresses_chunk in split_by_chunks(list(addresses), ORIGINATION_REQUEST_LIMIT):
                raw_originations += list(
                    await self._request_values_dict(
                        'get',
                        url='v1/operations/originations',
                        params={
                            **params,
                            'originatedContract.in': ','.join(addresses_chunk),
                        },
                    )
                )
        elif code_hashes and not addresses:
            raw_originations += list(
                await self._request_values_dict(
                    'get',
                    url='v1/operations/originations',
                    params={
                        **params,
                        # FIXME: Need a helper for this join
                        'codeHash.in': ','.join(str(h) for h in code_hashes),
                    },
                )
            )
        elif not addresses and not code_hashes:
            raw_originations += list(
                await self._request_values_dict(
                    'get',
                    url='v1/operations/originations',
                    params=params,
                )
            )
        elif addresses and code_hashes:
            raise FrameworkException('Either `addresses` or `code_hashes` should be specified')

        # NOTE: `type` field needs to be set manually when requesting operations by specific type
        return tuple(TzktOperationData.from_json(op, type_='origination') for op in raw_originations)

    async def get_transactions(
        self,
        field: str,
        addresses: set[str] | None,
        code_hashes: set[int] | None,
        first_level: int | None = None,
        last_level: int | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> tuple[TzktOperationData, ...]:
        params = self._get_request_params(
            first_level,
            last_level,
            offset,
            limit,
            TRANSACTION_OPERATION_FIELDS,
            cursor=True,
            values=True,
            status='applied',
            sort='level',
        )
        if addresses and not code_hashes:
            params[f'{field}.in'] = ','.join(addresses)
        elif code_hashes and not addresses:
            params[f'{field}CodeHash.in'] = ','.join(str(h) for h in code_hashes)

        raw_transactions = await self._request_values_dict(
            'get',
            url='v1/operations/transactions',
            params=params,
        )

        # NOTE: `type` field needs to be set manually when requesting operations by specific type
        return tuple(TzktOperationData.from_json(op, type_='transaction') for op in raw_transactions)

    async def iter_transactions(
        self,
        field: str,
        addresses: set[str],
        first_level: int,
        last_level: int,
    ) -> AsyncIterator[tuple[TzktOperationData, ...]]:
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
    ) -> tuple[TzktBigMapData, ...]:
        params = self._get_request_params(
            first_level=first_level,
            last_level=last_level,
            offset=offset,
            limit=limit,
        )
        raw_big_maps = await self.request(
            'get',
            url='v1/bigmaps/updates',
            params={
                **params,
                'contract.in': ','.join(addresses),
                'path.in': ','.join(paths),
            },
        )
        return tuple(TzktBigMapData.from_json(bm) for bm in raw_big_maps)

    async def iter_big_maps(
        self,
        addresses: set[str],
        paths: set[str],
        first_level: int,
        last_level: int,
    ) -> AsyncIterator[tuple[TzktBigMapData, ...]]:
        async for batch in self._iter_batches(
            self.get_big_maps,
            addresses,
            paths,
            first_level,
            last_level,
            cursor=False,
        ):
            yield batch

    async def get_quote(self, level: int) -> TzktQuoteData:
        """Get quote for block"""
        self._logger.info('Fetching quotes for level %s', level)
        quote_json = await self.request(
            'get',
            url='v1/quotes',
            params={'level': level},
        )
        return TzktQuoteData.from_json(quote_json[0])

    async def get_quotes(
        self,
        first_level: int,
        last_level: int,
        offset: int | None = None,
        limit: int | None = None,
    ) -> tuple[TzktQuoteData, ...]:
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
        return tuple(TzktQuoteData.from_json(quote) for quote in quotes_json)

    async def iter_quotes(
        self,
        first_level: int,
        last_level: int,
    ) -> AsyncIterator[tuple[TzktQuoteData, ...]]:
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
    ) -> tuple[TzktTokenTransferData, ...]:
        """Get token transfers for contract"""
        params = self._get_request_params(
            first_level,
            last_level,
            offset=offset or 0,
            limit=limit,
            select=TZKT_TOKEN_TRANSFER_DATA_FIELDS,
            values=True,
            cursor=True,
            **{
                'token.contract.in': ','.join(token_addresses),
                'token.id.in': ','.join(str(token_id) for token_id in token_ids),
                'from.in': ','.join(from_addresses),
                'to.in': ','.join(to_addresses),
            },
        )
        raw_token_transfers = await self._request_values_dict('get', url='v1/tokens/transfers', params=params)
        return tuple(TzktTokenTransferData.from_json(item) for item in raw_token_transfers)

    async def iter_token_transfers(
        self,
        token_addresses: set[str],
        token_ids: set[int],
        from_addresses: set[str],
        to_addresses: set[str],
        first_level: int,
        last_level: int,
    ) -> AsyncIterator[tuple[TzktTokenTransferData, ...]]:
        """Iterate token transfers for contract"""
        async for batch in self._iter_batches(
            self.get_token_transfers,
            token_addresses,
            token_ids,
            from_addresses,
            to_addresses,
            first_level,
            last_level,
            cursor=True,
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
    ) -> tuple[TzktEventData, ...]:
        # FIXME: no tests for function
        offset, limit = offset or 0, limit or self.request_limit
        raw_events = await self._request_values_dict(
            'get',
            url='v1/contracts/events',
            params={
                'contract.in': ','.join(addresses),
                'tag.in': ','.join(tags),
                'level.ge': first_level,
                'level.le': last_level,
                'select.values': ','.join(f.name for f in fields(TzktEventData)),
                'offset.cr': offset,
                'limit': limit,
            },
        )
        return tuple(TzktEventData.from_json(e) for e in raw_events)

    async def iter_events(
        self,
        addresses: set[str],
        tags: set[str],
        first_level: int,
        last_level: int,
    ) -> AsyncIterator[tuple[TzktEventData, ...]]:
        async for batch in self._iter_batches(
            self.get_events,
            addresses,
            tags,
            first_level,
            last_level,
            cursor=False,
        ):
            yield batch

    async def subscribe(self) -> None:
        missing_subscriptions = self._subscriptions.missing_subscriptions
        if not missing_subscriptions:
            return

        self._logger.info('Subscribing to %s channels', len(missing_subscriptions))
        for subscription in missing_subscriptions:
            if not isinstance(subscription, TzktSubscription):
                raise FrameworkException(f'Expected TzktSubscription, got {subscription}')
            await self._subscribe(subscription)
        self._logger.info('Subscribed to %s channels', len(missing_subscriptions))

    async def _subscribe(self, subscription: TzktSubscription) -> None:
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

    async def _request_values_dict(self, *args: Any, **kwargs: Any) -> tuple[dict[str, Any], ...]:
        # NOTE: basicaly this function create dict from list of tuples request
        # NOTE: this is necessary because for TZKT API cursor iteration is more efficient and asking only values is more efficient too """
        try:
            fields = kwargs.get('params', {})['select.values'].split(',')
        except KeyError as e:
            raise DatasourceError('No fields selected, no select.values param in request', self.name) from e
        if len(fields) == 1:
            raise DatasourceError(
                '_request_values_dict does not support one field request because tzkt will return plain list', self.name
            )

        # NOTE: select.values supported for methods with multiple objects in response only
        response: list[list[str]] = await self.request(*args, **kwargs)
        return tuple([dict(zip(fields, values)) for values in response])

    def _get_request_params(
        self,
        first_level: int | None = None,
        last_level: int | None = None,
        offset: int | None = None,
        limit: int | None = None,
        select: tuple[str, ...] | None = None,
        values: bool = False,  # return only list of chosen values instead of dict
        cursor: bool = False,
        sort: str | None = None,
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
            #  filter fields
            params['select.values' if values else 'select'] = ','.join(select)
        if sort:
            if sort.startswith('-'):
                sort_param_name = 'sort.desc'
                sort = sort[1:]
            else:
                sort_param_name = 'sort'
            params[sort_param_name] = sort
        return {
            **params,
            **kwargs,
        }

    async def _iter_batches(
        self,
        fn: Callable[..., Awaitable[Sequence[Any]]],
        *args: Any,
        cursor: bool = True,
        **kwargs: Any,
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

    def _get_signalr_client(self) -> SignalRClient:
        """Create SignalR client, register message callbacks"""
        if self._signalr_client:
            return self._signalr_client

        self._logger.info('Creating SignalR client')
        self._signalr_client = SignalRClient(
            url=f'{self._http._url}/v1/events',
            max_size=None,
        )

        self._signalr_client.on_open(self._on_connected)
        self._signalr_client.on_close(self._on_disconnected)
        self._signalr_client.on_error(self._on_error)

        self._signalr_client.on('operations', partial(self._on_message, TzktMessageType.operation))
        self._signalr_client.on('transfers', partial(self._on_message, TzktMessageType.token_transfer))
        self._signalr_client.on('bigmaps', partial(self._on_message, TzktMessageType.big_map))
        self._signalr_client.on('head', partial(self._on_message, TzktMessageType.head))
        self._signalr_client.on('events', partial(self._on_message, TzktMessageType.event))

        return self._signalr_client

    async def _send(
        self,
        method: str,
        arguments: list[dict[str, Any]],
        on_invocation: Callable[[CompletionMessage], Awaitable[None]] | None = None,
    ) -> None:
        client = self._get_signalr_client()
        await client.send(method, arguments, on_invocation)  # type: ignore[arg-type]

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

    async def _on_message(self, type_: TzktMessageType, message: list[dict[str, Any]]) -> None:
        """Parse message received from Websocket, ensure it's correct in the current context and yield data."""
        # NOTE: Parse messages and either buffer or yield data
        for item in message:
            action = TzktMessageAction(item['type'])
            # NOTE: Legacy, sync level returned by TzKT during negotiation
            if action == TzktMessageAction.STATE:
                continue

            message_level = item['state']
            channel_level = self.get_channel_level(type_)
            self._channel_levels[type_] = message_level

            self._logger.info(
                'Realtime message received: %s, %s, %s -> %s',
                type_.value,
                action.name,
                channel_level,
                message_level,
            )

            # NOTE: Put data messages to buffer by level
            if action == TzktMessageAction.DATA:
                self._buffer.add(type_, message_level, item['data'])

            # NOTE: Try to process rollback automatically, emit if failed
            elif action == TzktMessageAction.REORG:
                if self._buffer.rollback(type_, channel_level, message_level):
                    self._logger.info('Rolled back blocks were dropped from realtime message buffer')
                else:
                    self._logger.info('Rolled back blocks are not buffered; proceeding to database rollback')
                    await self.emit_rollback(type_, channel_level, message_level)

            else:
                raise NotImplementedError(f'Unknown message type: {action}')

        # NOTE: Process extensive data from buffer
        for buffered_message in self._buffer.yield_from():
            if buffered_message.type == TzktMessageType.operation:
                await self._process_operations_data(cast(list[dict[str, Any]], buffered_message.data))
            elif buffered_message.type == TzktMessageType.token_transfer:
                await self._process_token_transfers_data(cast(list[dict[str, Any]], buffered_message.data))
            elif buffered_message.type == TzktMessageType.big_map:
                await self._process_big_maps_data(cast(list[dict[str, Any]], buffered_message.data))
            elif buffered_message.type == TzktMessageType.head:
                await self._process_head_data(cast(dict[str, Any], buffered_message.data))
            elif buffered_message.type == TzktMessageType.event:
                await self._process_events_data(cast(list[dict[str, Any]], buffered_message.data))
            else:
                raise NotImplementedError(f'Unknown message type: {buffered_message.type}')

    async def _process_operations_data(self, data: list[dict[str, Any]]) -> None:
        """Parse and emit raw operations from WS"""
        level_operations: defaultdict[int, deque[TzktOperationData]] = defaultdict(deque)

        for operation_json in data:
            if operation_json['status'] != 'applied':
                continue
            if 'hash' in operation_json:
                operation = TzktOperationData.from_json(operation_json)
            else:
                operation = TzktOperationData.from_migration_json(operation_json)
            level_operations[operation.level].append(operation)

        for _level, operations in level_operations.items():
            await self.emit_operations(tuple(operations))

    async def _process_token_transfers_data(self, data: list[dict[str, Any]]) -> None:
        """Parse and emit raw token transfers from WS"""
        level_token_transfers: defaultdict[int, deque[TzktTokenTransferData]] = defaultdict(deque)

        for token_transfer_json in data:
            token_transfer = TzktTokenTransferData.from_json(token_transfer_json)
            level_token_transfers[token_transfer.level].append(token_transfer)

        for _level, token_transfers in level_token_transfers.items():
            await self.emit_token_transfers(tuple(token_transfers))

    async def _process_big_maps_data(self, data: list[dict[str, Any]]) -> None:
        """Parse and emit raw big map diffs from WS"""
        level_big_maps: defaultdict[int, deque[TzktBigMapData]] = defaultdict(deque)

        big_maps: deque[TzktBigMapData] = deque()
        for big_map_json in data:
            big_map = TzktBigMapData.from_json(big_map_json)
            level_big_maps[big_map.level].append(big_map)

        for _level, big_maps in level_big_maps.items():
            await self.emit_big_maps(tuple(big_maps))

    async def _process_head_data(self, data: dict[str, Any]) -> None:
        """Parse and emit raw head block from WS"""
        block = TzktHeadBlockData.from_json(data)
        await self.emit_head(block)

    async def _process_events_data(self, data: list[dict[str, Any]]) -> None:
        """Parse and emit raw big map diffs from WS"""
        level_events: defaultdict[int, deque[TzktEventData]] = defaultdict(deque)

        events: deque[TzktEventData] = deque()
        for event_json in data:
            event = TzktEventData.from_json(event_json)
            level_events[event.level].append(event)

        for _level, events in level_events.items():
            await self.emit_events(tuple(events))
