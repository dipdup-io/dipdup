from __future__ import annotations

import logging
import random
from abc import abstractmethod
from typing import TYPE_CHECKING
from typing import Any
from typing import Generic

from dipdup.config.tezos_operations import TezosOperationsHandlerOriginationPatternConfig as OriginationPatternConfig
from dipdup.config.tezos_operations import (
    TezosOperationsHandlerSmartRollupCementPatternConfig as SmartRollupCementPatternConfig,
)
from dipdup.config.tezos_operations import (
    TezosOperationsHandlerSmartRollupExecutePatternConfig as SmartRollupExecutePatternConfig,
)
from dipdup.config.tezos_operations import TezosOperationsHandlerTransactionPatternConfig as TransactionPatternConfig
from dipdup.config.tezos_operations import TezosOperationsIndexConfig
from dipdup.config.tezos_operations import TezosOperationsUnfilteredIndexConfig
from dipdup.datasources.tezos_tzkt import TezosTzktDatasource
from dipdup.exceptions import ConfigurationError
from dipdup.exceptions import FrameworkException
from dipdup.fetcher import FetcherChannel
from dipdup.fetcher import FilterT
from dipdup.indexes.tezos_tzkt import TezosTzktFetcher
from dipdup.models.tezos import TezosOperationData
from dipdup.models.tezos import TezosOperationType

if TYPE_CHECKING:
    from collections import defaultdict
    from collections import deque
    from collections.abc import AsyncIterator
    from collections.abc import Iterable


_logger = logging.getLogger('dipdup.fetcher')


def dedup_operations(operations: Iterable[TezosOperationData]) -> tuple[TezosOperationData, ...]:
    """Merge and sort operations fetched from multiple endpoints"""
    return tuple(
        sorted(
            (({op.id: op for op in operations}).values()),
            key=lambda op: op.id,
        )
    )


def get_operations_head(operations: tuple[TezosOperationData, ...]) -> int:
    """Get latest block level (head) of sorted operations batch"""
    for i in range(len(operations) - 1)[::-1]:
        if operations[i].level != operations[i + 1].level:
            return operations[i].level
    return operations[0].level


async def get_transaction_filters(
    config: TezosOperationsIndexConfig,
) -> tuple[set[str], set[int]]:
    """Get addresses to fetch transactions from during initial synchronization"""
    if TezosOperationType.transaction not in config.types:
        return set(), set()

    code_hash: int | str | None
    addresses: set[str] = set()
    hashes: set[int] = set()

    # NOTE: Don't try to guess contracts from handlers if set implicitly
    if config.contracts:
        for contract in config.contracts:
            if contract.address:
                addresses.add(contract.address)
            elif contract.resolved_code_hash:
                hashes.add(contract.resolved_code_hash)

        return addresses, hashes

    for handler_config in config.handlers:
        for pattern_config in handler_config.pattern:
            if not isinstance(pattern_config, TransactionPatternConfig):
                continue

            if pattern_config.source:
                if address := pattern_config.source.address:
                    addresses.add(address)
                if code_hash := pattern_config.source.resolved_code_hash:
                    hashes.add(code_hash)

            if pattern_config.destination:
                if address := pattern_config.destination.address:
                    addresses.add(address)
                if code_hash := pattern_config.destination.resolved_code_hash:
                    hashes.add(code_hash)

    return addresses, hashes


async def get_origination_filters(
    config: TezosOperationsIndexConfig,
    datasources: tuple[TezosTzktDatasource, ...],
) -> tuple[set[str], set[int]]:
    """Get addresses to fetch origination from during initial synchronization"""
    if TezosOperationType.origination not in config.types:
        return set(), set()

    addresses: set[str] = set()
    hashes: set[int] = set()

    for handler_config in config.handlers:
        for pattern_config in handler_config.pattern:
            if not isinstance(pattern_config, OriginationPatternConfig):
                continue

            if pattern_config.originated_contract:
                if address := pattern_config.originated_contract.address:
                    addresses.add(address)
                if code_hash := pattern_config.originated_contract.resolved_code_hash:
                    hashes.add(code_hash)

            if pattern_config.source:
                _logger.warning(
                    "`source.address` filter significantly hurts indexing performance and doesn't support strict"
                    " typing. Consider using `originated_contract.code_hash` instead"
                )
                if address := pattern_config.source.address:
                    datasource = random.choice(datasources)
                    async for batch in datasource.iter_originated_contracts(address):
                        addresses.update(item['address'] for item in batch)
                if code_hash := pattern_config.source.resolved_code_hash:
                    raise FrameworkException('Invalid transaction filter `source.code_hash`')

    return addresses, hashes


async def get_sr_execute_filters(
    config: TezosOperationsIndexConfig,
) -> set[str]:
    """Get addresses to fetch smart rollup executions from during initial synchronization"""
    if TezosOperationType.sr_execute not in config.types:
        return set()

    addresses: set[str] = set()

    if config.contracts:
        for contract in config.contracts:
            if contract.address:
                addresses.add(contract.address)

    for handler_config in config.handlers:
        for pattern_config in handler_config.pattern:
            if not isinstance(pattern_config, SmartRollupExecutePatternConfig):
                continue

            if pattern_config.source:
                if address := pattern_config.source.address:
                    addresses.add(address)
                if pattern_config.source.resolved_code_hash:
                    raise ConfigurationError('Invalid `sr_execute` filter: `source.code_hash`')

            if pattern_config.destination:
                if address := pattern_config.destination.address:
                    addresses.add(address)
                if pattern_config.destination.resolved_code_hash:
                    raise ConfigurationError('Invalid `sr_execute` filter: `destination.code_hash`')

    addresses = {a for a in addresses if a.startswith('sr1')}
    _logger.info('Fetching smart rollup executions from %s addresses', len(addresses))
    return addresses


async def get_sr_cement_filters(
    config: TezosOperationsIndexConfig,
) -> set[str]:
    """Get addresses to fetch smart rollup cement commitments from during initial synchronization"""
    if TezosOperationType.sr_cement not in config.types:
        return set()

    addresses: set[str] = set()

    if config.contracts:
        for contract in config.contracts:
            if contract.address:
                addresses.add(contract.address)

    for handler_config in config.handlers:
        for pattern_config in handler_config.pattern:
            if not isinstance(pattern_config, SmartRollupCementPatternConfig):
                continue

            if pattern_config.source:
                if address := pattern_config.source.address:
                    addresses.add(address)
                if pattern_config.source.resolved_code_hash:
                    raise ConfigurationError('Invalid `sr_cement` filter: `source.code_hash`')

            if pattern_config.destination:
                if address := pattern_config.destination.address:
                    addresses.add(address)
                if pattern_config.destination.resolved_code_hash:
                    raise ConfigurationError('Invalid `sr_cement` filter: `destination.code_hash`')

    addresses = {a for a in addresses if a.startswith('sr1')}
    _logger.info('Fetching smart rollup cemented commitments from %s addresses', len(addresses))
    return addresses


class OriginationAddressFetcherChannel(FetcherChannel[TezosOperationData, TezosTzktDatasource, str]):

    _offset: int | None

    async def fetch(self) -> None:
        if not self._filter:
            self._head = self._last_level
            self._offset = self._last_level
            return

        # FIXME: No pagination because of URL length limit workaround
        originations = await self.random_datasource.get_originations(
            addresses=self._filter,
            first_level=self._first_level,
            last_level=self._last_level,
        )

        for op in originations:
            self._buffer[op.level].append(op)

        self._head = self._last_level
        self._offset = self._last_level


class OriginationHashFetcherChannel(FetcherChannel[TezosOperationData, TezosTzktDatasource, int]):

    _offset: int | None

    async def fetch(self) -> None:
        if not self._filter:
            self._head = self._last_level
            self._offset = self._last_level
            return

        datasource = self.random_datasource
        originations = await datasource.get_originations(
            code_hashes=self._filter,
            offset=self._offset,
            first_level=self._first_level,
            last_level=self._last_level,
        )

        for op in originations:
            self._buffer[op.level].append(op)

        if len(originations) < datasource.request_limit:
            self._head = self._last_level
        else:
            self._offset = originations[-1].id
            self._head = get_operations_head(originations)


class MigrationOriginationFetcherChannel(FetcherChannel[TezosOperationData, TezosTzktDatasource, None]):

    _offset: int | None

    async def fetch(self) -> None:
        if self._filter:
            raise FrameworkException("Migration origination fetcher channel doesn't support filters")

        datasource = self.random_datasource
        originations = await datasource.get_migration_originations(
            first_level=self._first_level,
            last_level=self._last_level,
            offset=self._offset,
        )

        for op in originations:
            if op.originated_contract_address:
                code_hash, type_hash = await datasource.get_contract_hashes(op.originated_contract_address)
                op_dict = op.__dict__
                op_dict.update(
                    originated_contract_code_hash=code_hash,
                    originated_contract_type_hash=type_hash,
                )
                op = TezosOperationData(**op_dict)

            self._buffer[op.level].append(op)

        if len(originations) < datasource.request_limit:
            self._head = self._last_level
        else:
            self._offset = originations[-1].id
            self._head = get_operations_head(originations)


class TransactionBaseFetcherChannel(FetcherChannel[TezosOperationData, TezosTzktDatasource, FilterT], Generic[FilterT]):
    def __init__(
        self,
        buffer: defaultdict[int, deque[TezosOperationData]],
        filter: set[FilterT],
        first_level: int,
        last_level: int,
        datasources: tuple[TezosTzktDatasource, ...],
        field: str,
    ) -> None:
        super().__init__(buffer, filter, first_level, last_level, datasources)
        self._field = field
        # FIXME: First datasource only
        self._datasource = self._datasources[0]

    _offset: int | None

    @abstractmethod
    async def _get_transactions(self) -> tuple[TezosOperationData, ...]:
        raise NotImplementedError

    async def fetch(self) -> None:
        if not self._filter:
            self._head = self._last_level
            self._offset = self._last_level
            return

        transactions = await self._get_transactions()

        for op in transactions:
            self._buffer[op.level].append(op)

        if len(transactions) < self._datasource.request_limit:
            self._head = self._last_level
        else:
            self._offset = transactions[-1].id
            self._head = get_operations_head(transactions)


class TransactionAddressFetcherChannel(TransactionBaseFetcherChannel[str]):
    _offset: int | None

    async def _get_transactions(self) -> tuple[TezosOperationData, ...]:
        return await self._datasource.get_transactions(
            field=self._field,
            addresses=self._filter,
            code_hashes=None,
            offset=self._offset,
            first_level=self._first_level,
            last_level=self._last_level,
        )


class TransactionHashFetcherChannel(TransactionBaseFetcherChannel[int]):
    _offset: int | None

    async def _get_transactions(self) -> tuple[TezosOperationData, ...]:
        return await self._datasource.get_transactions(
            field=self._field,
            addresses=None,
            code_hashes=self._filter,
            offset=self._offset,
            first_level=self._first_level,
            last_level=self._last_level,
        )


class SmartRollupExecuteAddressFetcherChannel(FetcherChannel[TezosOperationData, TezosTzktDatasource, str]):
    _offset: int | None

    def __init__(
        self,
        buffer: defaultdict[int, deque[TezosOperationData]],
        filter: set[str],
        first_level: int,
        last_level: int,
        datasources: tuple[TezosTzktDatasource, ...],
        field: str,
    ) -> None:
        super().__init__(buffer, filter, first_level, last_level, datasources)
        self._field = field

    async def fetch(self) -> None:
        if not self._filter:
            self._head = self._last_level
            self._offset = self._last_level
            return

        datasource = self.random_datasource
        operations = await datasource.get_sr_execute(
            field=self._field,
            addresses=self._filter,
            offset=self._offset,
            first_level=self._first_level,
            last_level=self._last_level,
        )

        for op in operations:
            self._buffer[op.level].append(op)

        if len(operations) < datasource.request_limit:
            self._head = self._last_level
        else:
            self._offset = operations[-1].id
            self._head = get_operations_head(operations)


class OperationsUnfilteredFetcherChannel(FetcherChannel[TezosOperationData, TezosTzktDatasource, None]):
    _offset: int | None

    def __init__(
        self,
        buffer: defaultdict[int, deque[TezosOperationData]],
        first_level: int,
        last_level: int,
        datasources: tuple[TezosTzktDatasource, ...],
        type: TezosOperationType,
    ) -> None:
        super().__init__(buffer, set(), first_level, last_level, datasources)
        self._type = type

    async def fetch(self) -> None:
        datasource = self.random_datasource
        match self._type:
            case TezosOperationType.origination:
                operations = await datasource.get_originations(
                    addresses=None,
                    code_hashes=None,
                    first_level=self._first_level,
                    last_level=self._last_level,
                    offset=self._offset,
                )
            case TezosOperationType.transaction:
                operations = await datasource.get_transactions(
                    field='',
                    addresses=None,
                    code_hashes=None,
                    first_level=self._first_level,
                    last_level=self._last_level,
                    offset=self._offset,
                )
            case TezosOperationType.sr_execute:
                operations = await datasource.get_sr_execute(
                    field='',
                    addresses=None,
                    first_level=self._first_level,
                    last_level=self._last_level,
                    offset=self._offset,
                )
            case _:
                raise FrameworkException('Unsupported operation type')

        for op in operations:
            self._buffer[op.level].append(op)

        if len(operations) < datasource.request_limit:
            self._head = self._last_level
        else:
            self._offset = operations[-1].id
            self._head = get_operations_head(operations)


class OperationsFetcher(TezosTzktFetcher[TezosOperationData]):
    """Fetches operations from multiple REST API endpoints, merges them and yields by level.

    Offset of every endpoint is tracked separately.
    """

    def __init__(
        self,
        name: str,
        datasources: tuple[TezosTzktDatasource, ...],
        first_level: int,
        last_level: int,
        transaction_addresses: set[str],
        transaction_hashes: set[int],
        origination_addresses: set[str],
        origination_hashes: set[int],
        sr_execute_addresses: set[str],
        migration_originations: bool = False,
    ) -> None:
        super().__init__(name, datasources, first_level, last_level)
        self._transaction_addresses = transaction_addresses
        self._transaction_hashes = transaction_hashes
        self._origination_addresses = origination_addresses
        self._origination_hashes = origination_hashes
        self._sr_execute_addresses = sr_execute_addresses
        self._migration_originations = migration_originations

    @classmethod
    async def create(
        cls,
        config: TezosOperationsIndexConfig,
        datasources: tuple[TezosTzktDatasource, ...],
        first_level: int,
        last_level: int,
    ) -> OperationsFetcher:
        transaction_addresses, transaction_hashes = await get_transaction_filters(config)
        origination_addresses, origination_hashes = await get_origination_filters(config, datasources)
        sr_execute_addresses = await get_sr_execute_filters(config)

        return OperationsFetcher(
            name=config.name,
            datasources=datasources,
            first_level=first_level,
            last_level=last_level,
            transaction_addresses=transaction_addresses,
            transaction_hashes=transaction_hashes,
            origination_addresses=origination_addresses,
            origination_hashes=origination_hashes,
            sr_execute_addresses=sr_execute_addresses,
            migration_originations=TezosOperationType.migration in config.types,
        )

    async def fetch_by_level(self) -> AsyncIterator[tuple[int, tuple[TezosOperationData, ...]]]:
        """Iterate over operations fetched with multiple REST requests with different filters.

        Resulting data is split by level, deduped, sorted and ready to be processed by TezosOperationsIndex.
        """
        channel_kwargs = {
            'buffer': self._buffer,
            'datasources': self._datasources,
            'first_level': self._first_level,
            'last_level': self._last_level,
        }
        channels: tuple[FetcherChannel[TezosOperationData, Any, Any], ...] = (
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
            SmartRollupExecuteAddressFetcherChannel(
                filter=self._sr_execute_addresses,
                field='sender',
                **channel_kwargs,  # type: ignore[arg-type]
            ),
            SmartRollupExecuteAddressFetcherChannel(
                filter=self._sr_execute_addresses,
                field='rollup',
                **channel_kwargs,  # type: ignore[arg-type]
            ),
        )

        operations_iter = self._merged_iter(
            channels=set(channels),
            sort_fn=dedup_operations,
        )
        async for level, operations in self.readahead_by_level(operations_iter):
            yield level, operations


class OperationsUnfilteredFetcher(TezosTzktFetcher[TezosOperationData]):
    def __init__(
        self,
        name: str,
        datasources: tuple[TezosTzktDatasource, ...],
        first_level: int,
        last_level: int,
        transactions: bool,
        originations: bool,
        migration_originations: bool,
    ) -> None:
        super().__init__(name, datasources, first_level, last_level)
        self._transactions = transactions
        self._originations = originations
        self._migration_originations = migration_originations

    @classmethod
    async def create(
        cls,
        config: TezosOperationsUnfilteredIndexConfig,
        datasources: tuple[TezosTzktDatasource, ...],
        first_level: int,
        last_level: int,
    ) -> OperationsUnfilteredFetcher:
        return OperationsUnfilteredFetcher(
            name=config.name,
            datasources=datasources,
            first_level=first_level,
            last_level=last_level,
            transactions=TezosOperationType.transaction in config.types,
            originations=TezosOperationType.origination in config.types,
            migration_originations=TezosOperationType.migration in config.types,
        )

    async def fetch_by_level(self) -> AsyncIterator[tuple[int, tuple[TezosOperationData, ...]]]:
        """Iterate over operations fetched with multiple REST requests with different filters.

        Resulting data is split by level, deduped, sorted and ready to be processed by TezosOperationsIndex.
        """
        channel_kwargs = {
            'buffer': self._buffer,
            'datasources': self._datasources,
            'first_level': self._first_level,
            'last_level': self._last_level,
        }
        channels: list[FetcherChannel[TezosOperationData, Any, Any]] = []
        if self._transactions:
            channels.append(
                OperationsUnfilteredFetcherChannel(
                    type=TezosOperationType.transaction,
                    **channel_kwargs,  # type: ignore[arg-type]
                ),
            )
        if self._originations:
            channels.append(
                OperationsUnfilteredFetcherChannel(
                    type=TezosOperationType.origination,
                    **channel_kwargs,  # type: ignore[arg-type]
                ),
            )
        if self._migration_originations:
            channels.append(
                MigrationOriginationFetcherChannel(
                    filter=set(),
                    **channel_kwargs,  # type: ignore[arg-type]
                ),
            )

        operations_iter = self._merged_iter(
            channels=set(channels),
            sort_fn=dedup_operations,
        )
        async for level, operations in self.readahead_by_level(operations_iter):
            yield level, operations
