from __future__ import annotations

import logging
from collections import defaultdict
from collections import deque
from typing import Any
from typing import AsyncIterator

from dipdup.config import OperationHandlerOriginationPatternConfig as OriginationPatternConfig
from dipdup.config import OperationHandlerTransactionPatternConfig as TransactionPatternConfig
from dipdup.config import OperationIndexConfig
from dipdup.config import OperationUnfilteredIndexConfig
from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.enums import OperationType
from dipdup.exceptions import FrameworkException
from dipdup.fetcher import DataFetcher
from dipdup.fetcher import FetcherChannel
from dipdup.models import OperationData

_logger = logging.getLogger('dipdup.fetcher')


def dedup_operations(operations: tuple[OperationData, ...]) -> tuple[OperationData, ...]:
    """Merge and sort operations fetched from multiple endpoints"""
    return tuple(
        sorted(
            (({op.id: op for op in operations}).values()),
            key=lambda op: op.id,
        )
    )


def get_operations_head(operations: tuple[OperationData, ...]) -> int:
    """Get latest block level (head) of sorted operations batch"""
    for i in range(len(operations) - 1)[::-1]:
        if operations[i].level != operations[i + 1].level:
            return operations[i].level
    return operations[0].level


async def get_transaction_filters(
    config: OperationIndexConfig,
    datasource: TzktDatasource,
) -> tuple[set[str], set[int]]:
    """Get addresses to fetch transactions from during initial synchronization"""
    if OperationType.transaction not in config.types:
        return set(), set()

    code_hash: int | str | None
    addresses: set[str] = set()
    hashes: set[int] = set()

    # NOTE: Don't try to guess contracts from handlers if set implicitly
    if config.contracts:
        for contract in config.contracts:
            if contract.address:
                addresses.add(contract.address)
            if isinstance(contract.code_hash, int):
                hashes.add(contract.code_hash)
            elif isinstance(contract.code_hash, str):
                code_hash, _ = await datasource.get_contract_hashes(contract.code_hash)
                hashes.add(code_hash)

        return addresses, hashes

    for handler_config in config.handlers:
        for pattern_config in handler_config.pattern:
            if not isinstance(pattern_config, TransactionPatternConfig):
                continue

            if pattern_config.source:
                if address := pattern_config.source.address:
                    addresses.add(address)
                if code_hash := pattern_config.source.code_hash:
                    if isinstance(code_hash, str):
                        code_hash, _ = await datasource.get_contract_hashes(code_hash)
                        pattern_config.source.code_hash = code_hash
                    hashes.add(code_hash)

            if pattern_config.destination:
                if address := pattern_config.destination.address:
                    addresses.add(address)
                if code_hash := pattern_config.destination.code_hash:
                    if isinstance(code_hash, str):
                        code_hash, _ = await datasource.get_contract_hashes(code_hash)
                        pattern_config.destination.code_hash = code_hash
                    hashes.add(code_hash)

    _logger.info(f'Fetching transactions from {len(addresses)} addresses and {len(hashes)} code hashes')
    return addresses, hashes


async def get_origination_filters(
    config: OperationIndexConfig,
    datasource: TzktDatasource,
) -> tuple[set[str], set[int]]:
    """Get addresses to fetch origination from during initial synchronization"""
    if OperationType.origination not in config.types:
        return set(), set()

    addresses: set[str] = set()
    hashes: set[int] = set()

    for handler_config in config.handlers:
        for pattern_config in handler_config.pattern:
            if not isinstance(pattern_config, OriginationPatternConfig):
                continue

            # TODO: Remove in 7.0
            if pattern_config.similar_to:
                raise FrameworkException('originated_contract` alias, should be replaced in __init__')

            if pattern_config.originated_contract:
                if address := pattern_config.originated_contract.address:
                    addresses.add(address)
                if code_hash := pattern_config.originated_contract.code_hash:
                    if isinstance(code_hash, str):
                        code_hash, _ = await datasource.get_contract_hashes(code_hash)
                        pattern_config.originated_contract.code_hash = code_hash
                    hashes.add(code_hash)

            if pattern_config.source:
                _logger.warning(
                    "`source.address` filter significantly hurts indexing performance and doesn't support strict typing. "
                    'Consider using `originated_contract.code_hash` instead'
                )
                if address := pattern_config.source.address:
                    async for batch in datasource.iter_originated_contracts(address):
                        addresses.update(batch)
                if code_hash := pattern_config.source.code_hash:
                    raise FrameworkException('Invalid transaction filter `source.code_hash`')

    _logger.info(f'Fetching originations from {len(addresses)} addresses and {len(hashes)} code hashes')
    return addresses, hashes


class OriginationAddressFetcherChannel(FetcherChannel[OperationData, str]):
    async def fetch(self) -> None:
        if not self._filter:
            self._head = self._last_level
            self._offset = self._last_level
            return

        # FIXME: No pagination because of URL length limit workaround
        originations = await self._datasource.get_originations(
            addresses=self._filter,
            first_level=self._first_level,
            last_level=self._last_level,
        )

        for op in originations:
            self._buffer[op.level].append(op)

        self._head = self._last_level
        self._offset = self._last_level


class OriginationHashFetcherChannel(FetcherChannel[OperationData, int]):
    async def fetch(self) -> None:
        if not self._filter:
            self._head = self._last_level
            self._offset = self._last_level
            return

        originations = await self._datasource.get_originations(
            code_hashes=self._filter,
            offset=self._offset,
            first_level=self._first_level,
            last_level=self._last_level,
        )

        for op in originations:
            self._buffer[op.level].append(op)

        if len(originations) < self._datasource.request_limit:
            self._head = self._last_level
        else:
            self._offset = originations[-1].id
            self._head = get_operations_head(originations)


class MigrationOriginationFetcherChannel(FetcherChannel[OperationData, None]):
    async def fetch(self) -> None:
        if self._filter:
            raise FrameworkException("Migration origination fetcher channel doesn't support filters")

        originations = await self._datasource.get_migration_originations(
            first_level=self._first_level,
            last_level=self._last_level,
            offset=self._offset,
        )

        for op in originations:
            if op.originated_contract_address:
                code_hash, type_hash = await self._datasource.get_contract_hashes(op.originated_contract_address)
                op.originated_contract_code_hash = code_hash
                op.originated_contract_type_hash = type_hash

            self._buffer[op.level].append(op)

        if len(originations) < self._datasource.request_limit:
            self._head = self._last_level
        else:
            self._offset = originations[-1].id
            self._head = get_operations_head(originations)


class TransactionAddressFetcherChannel(FetcherChannel[OperationData, str]):
    def __init__(
        self,
        buffer: defaultdict[int, deque[OperationData]],
        filter: set[str],
        first_level: int,
        last_level: int,
        datasource: TzktDatasource,
        field: str,
    ) -> None:
        super().__init__(buffer, filter, first_level, last_level, datasource)
        self._field = field

    async def fetch(self) -> None:
        if not self._filter:
            self._head = self._last_level
            self._offset = self._last_level
            return

        transactions = await self._datasource.get_transactions(
            field=self._field,
            addresses=self._filter,
            code_hashes=None,
            offset=self._offset,
            first_level=self._first_level,
            last_level=self._last_level,
        )

        for op in transactions:
            level = op.level
            self._buffer[level].append(op)

        if len(transactions) < self._datasource.request_limit:
            self._head = self._last_level
        else:
            self._offset = transactions[-1].id
            self._head = get_operations_head(transactions)


class TransactionHashFetcherChannel(FetcherChannel[OperationData, int]):
    def __init__(
        self,
        buffer: defaultdict[int, deque[OperationData]],
        filter: set[int],
        first_level: int,
        last_level: int,
        datasource: TzktDatasource,
        field: str,
    ) -> None:
        super().__init__(buffer, filter, first_level, last_level, datasource)
        self._field = field

    async def fetch(self) -> None:
        if not self._filter:
            self._head = self._last_level
            self._offset = self._last_level
            return

        transactions = await self._datasource.get_transactions(
            field=self._field,
            addresses=None,
            code_hashes=self._filter,
            offset=self._offset,
            first_level=self._first_level,
            last_level=self._last_level,
        )

        for op in transactions:
            self._buffer[op.level].append(op)

        if len(transactions) < self._datasource.request_limit:
            self._head = self._last_level
        else:
            self._offset = transactions[-1].id
            self._head = get_operations_head(transactions)


class OperationUnfilteredFetcherChannel(FetcherChannel[OperationData, None]):
    def __init__(
        self,
        buffer: defaultdict[int, deque[OperationData]],
        first_level: int,
        last_level: int,
        datasource: TzktDatasource,
        type: OperationType,
    ) -> None:
        super().__init__(buffer, set(), first_level, last_level, datasource)
        self._type = type

    async def fetch(self) -> None:
        if self._type == OperationType.origination:
            operations = await self._datasource.get_originations(
                addresses=None,
                code_hashes=None,
                first_level=self._first_level,
                last_level=self._last_level,
                offset=self._offset,
            )
        elif self._type == OperationType.transaction:
            operations = await self._datasource.get_transactions(
                field='',
                addresses=None,
                code_hashes=None,
                first_level=self._first_level,
                last_level=self._last_level,
                offset=self._offset,
            )
        else:
            raise FrameworkException('Unsupported operation type')

        for op in operations:
            self._buffer[op.level].append(op)

        if len(operations) < self._datasource.request_limit:
            self._head = self._last_level
        else:
            self._offset = operations[-1].id
            self._head = get_operations_head(operations)


class OperationFetcher(DataFetcher[OperationData]):
    """Fetches operations from multiple REST API endpoints, merges them and yields by level.

    Offet of every endpoint is tracked separately.
    """

    def __init__(
        self,
        datasource: TzktDatasource,
        first_level: int,
        last_level: int,
        transaction_addresses: set[str],
        transaction_hashes: set[int],
        origination_addresses: set[str],
        origination_hashes: set[int],
        migration_originations: bool = False,
    ) -> None:
        super().__init__(datasource, first_level, last_level)
        self._transaction_addresses = transaction_addresses
        self._transaction_hashes = transaction_hashes
        self._origination_addresses = origination_addresses
        self._origination_hashes = origination_hashes
        self._migration_originations = migration_originations

    @classmethod
    async def create(
        cls,
        config: OperationIndexConfig,
        datasource: TzktDatasource,
        first_level: int,
        last_level: int,
    ) -> OperationFetcher:
        transaction_addresses, transaction_hashes = await get_transaction_filters(config, datasource)
        origination_addresses, origination_hashes = await get_origination_filters(config, datasource)

        return OperationFetcher(
            datasource=datasource,
            first_level=first_level,
            last_level=last_level,
            transaction_addresses=transaction_addresses,
            transaction_hashes=transaction_hashes,
            origination_addresses=origination_addresses,
            origination_hashes=origination_hashes,
            migration_originations=OperationType.migration in config.types,
        )

    async def fetch_by_level(self) -> AsyncIterator[tuple[int, tuple[OperationData, ...]]]:
        """Iterate over operations fetched with multiple REST requests with different filters.

        Resulting data is splitted by level, deduped, sorted and ready to be processed by OperationIndex.
        """
        channel_kwargs = {
            'buffer': self._buffer,
            'datasource': self._datasource,
            'first_level': self._first_level,
            'last_level': self._last_level,
        }
        channels: tuple[FetcherChannel[OperationData, Any], ...] = (
            TransactionAddressFetcherChannel(
                filter=self._transaction_addresses,
                field='sender',
                **channel_kwargs,  # type: ignore[arg-type]
            ),
            TransactionAddressFetcherChannel(
                filter=self._transaction_addresses,
                field='target',
                **channel_kwargs,  # type: ignore[arg-type]
            ),
            TransactionHashFetcherChannel(
                filter=self._transaction_hashes,
                field='sender',
                **channel_kwargs,  # type: ignore[arg-type]
            ),
            TransactionHashFetcherChannel(
                filter=self._transaction_hashes,
                field='target',
                **channel_kwargs,  # type: ignore[arg-type]
            ),
            OriginationAddressFetcherChannel(
                filter=self._origination_addresses,
                **channel_kwargs,  # type: ignore[arg-type]
            ),
            OriginationHashFetcherChannel(
                filter=self._origination_hashes,
                **channel_kwargs,  # type: ignore[arg-type]
            ),
        )

        while True:
            min_channel = sorted(channels, key=lambda x: x.head)[0]
            await min_channel.fetch()

            # NOTE: It's a different channel now, but with greater head level
            min_channel = sorted(channels, key=lambda x: x.head)[0]
            min_head = min_channel.head

            while self._head <= min_head:
                if self._head in self._buffer:
                    operations = self._buffer.pop(self._head)
                    yield self._head, dedup_operations(tuple(operations))
                self._head += 1

            if all(c.fetched for c in channels):
                break

        if self._buffer:
            raise FrameworkException('Operations left in queue')


class OperationUnfilteredFetcher(DataFetcher[OperationData]):
    def __init__(
        self,
        datasource: TzktDatasource,
        first_level: int,
        last_level: int,
        transactions: bool,
        originations: bool,
        migration_originations: bool,
    ) -> None:
        super().__init__(datasource, first_level, last_level)
        self._transactions = transactions
        self._originations = originations
        self._migration_originations = migration_originations

    @classmethod
    async def create(
        cls,
        config: OperationUnfilteredIndexConfig,
        datasource: TzktDatasource,
        first_level: int,
        last_level: int,
    ) -> OperationUnfilteredFetcher:
        return OperationUnfilteredFetcher(
            datasource=datasource,
            first_level=first_level,
            last_level=last_level,
            transactions=OperationType.transaction in config.types,
            originations=OperationType.origination in config.types,
            migration_originations=OperationType.migration in config.types,
        )

    async def fetch_by_level(self) -> AsyncIterator[tuple[int, tuple[OperationData, ...]]]:
        """Iterate over operations fetched with multiple REST requests with different filters.

        Resulting data is splitted by level, deduped, sorted and ready to be processed by OperationIndex.
        """
        channel_kwargs = {
            'buffer': self._buffer,
            'datasource': self._datasource,
            'first_level': self._first_level,
            'last_level': self._last_level,
        }
        channels: tuple[FetcherChannel[OperationData, Any], ...] = ()
        if self._transactions:
            channels += (
                OperationUnfilteredFetcherChannel(
                    type=OperationType.transaction,
                    **channel_kwargs,  # type: ignore[arg-type]
                ),
            )
        if self._originations:
            channels += (
                OperationUnfilteredFetcherChannel(
                    type=OperationType.origination,
                    **channel_kwargs,  # type: ignore[arg-type]
                ),
            )
        if self._migration_originations:
            channels += (
                MigrationOriginationFetcherChannel(
                    filter=set(),
                    **channel_kwargs,  # type: ignore[arg-type]
                ),
            )

        while True:
            min_channel = sorted(channels, key=lambda x: x.head)[0]
            await min_channel.fetch()

            # NOTE: It's a different channel now, but with greater head level
            min_channel = sorted(channels, key=lambda x: x.head)[0]
            min_head = min_channel.head

            while self._head <= min_head:
                if self._head in self._buffer:
                    operations = self._buffer.pop(self._head)
                    yield self._head, dedup_operations(tuple(operations))
                self._head += 1

            if all(c.fetched for c in channels):
                break

        if self._buffer:
            raise FrameworkException('Operations left in queue')
