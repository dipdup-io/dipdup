from __future__ import annotations

import logging
from abc import ABC
from abc import abstractmethod
from collections import defaultdict
from collections import deque
from typing import TYPE_CHECKING
from typing import Any
from typing import AsyncGenerator
from typing import AsyncIterator
from typing import Generic
from typing import Protocol
from typing import TypeVar

from dipdup.exceptions import FrameworkException
from dipdup.models import BigMapData
from dipdup.models import EventData
from dipdup.models import OperationData
from dipdup.models import TokenTransferData

if TYPE_CHECKING:
    from dipdup.datasources.tzkt.datasource import TzktDatasource


class HasLevel(Protocol):
    level: int


Level = int
FetcherBufferT = TypeVar('FetcherBufferT', bound=HasLevel)
FetcherFilterT = TypeVar('FetcherFilterT')


async def yield_by_level(
    iterable: AsyncIterator[tuple[FetcherBufferT, ...]]
) -> AsyncGenerator[tuple[Level, tuple[FetcherBufferT, ...]], None]:
    items: tuple[FetcherBufferT, ...] = ()

    async for item_batch in iterable:
        items = items + item_batch

        # NOTE: Yield slices by level except the last one
        while True:
            for i in range(len(items) - 1):
                curr_level, next_level = items[i].level, items[i + 1].level

                # NOTE: Level boundaries found. Exit for loop, stay in while.
                if curr_level != next_level:
                    yield curr_level, items[: i + 1]
                    items = items[i + 1 :]
                    break
            else:
                break

    if items:
        yield items[0].level, items


def dedup_operations(operations: tuple[OperationData, ...]) -> tuple[OperationData, ...]:
    """Merge and sort operations fetched from multiple endpoints"""
    return tuple(
        sorted(
            (({op.id: op for op in operations}).values()),
            key=lambda op: op.id,
        )
    )


# TODO: Move back to op.fetcher
def get_operations_head(operations: tuple[OperationData, ...]) -> int:
    """Get latest block level (head) of sorted operations batch"""
    for i in range(len(operations) - 1)[::-1]:
        if operations[i].level != operations[i + 1].level:
            return operations[i].level
    return operations[0].level


class FetcherChannel(ABC, Generic[FetcherBufferT, FetcherFilterT]):
    def __init__(
        self,
        buffer: defaultdict[Level, deque[FetcherBufferT]],
        filter: set[FetcherFilterT],
        first_level: int,
        last_level: int,
        datasource: 'TzktDatasource',
    ) -> None:
        super().__init__()
        self._buffer = buffer
        self._filter = filter
        self._first_level = first_level
        self._last_level = last_level
        self._datasource = datasource

        self._head: int = 0
        self._offset: int = 0

    @property
    def head(self) -> int:
        return self._head

    @property
    def fetched(self) -> bool:
        return self._head >= self._last_level

    @abstractmethod
    async def fetch(self) -> None:
        """Fetch a single `requets_limit` batch of items, bump channel offset"""
        ...


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


class TransactionAddressFetcherChannel(FetcherChannel[OperationData, str]):
    def __init__(
        self,
        buffer: defaultdict[Level, deque[OperationData]],
        filter: set[str],
        first_level: int,
        last_level: int,
        datasource: 'TzktDatasource',
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
        buffer: defaultdict[Level, deque[OperationData]],
        filter: set[int],
        first_level: int,
        last_level: int,
        datasource: 'TzktDatasource',
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


class DataFetcher(ABC, Generic[FetcherBufferT]):
    def __init__(
        self,
        datasource: 'TzktDatasource',
        first_level: int,
        last_level: int,
    ) -> None:
        self._datasource = datasource
        self._first_level = first_level
        self._last_level = last_level
        self._buffer: defaultdict[Level, deque[FetcherBufferT]] = defaultdict(deque)
        self._head = 0

    @abstractmethod
    def fetch_by_level(self) -> AsyncIterator[tuple[int, tuple[FetcherBufferT, ...]]]:
        ...


class OperationFetcher(DataFetcher[OperationData]):
    """Fetches operations from multiple REST API endpoints, merges them and yields by level.

    Offet of every endpoint is tracked separately.
    """

    def __init__(
        self,
        datasource: 'TzktDatasource',
        first_level: int,
        last_level: int,
        transaction_addresses: set[str],
        transaction_hashes: set[int],
        origination_addresses: set[str],
        origination_hashes: set[int],
        migration_originations: tuple[OperationData, ...] = (),
    ) -> None:
        super().__init__(datasource, first_level, last_level)
        self._transaction_addresses = transaction_addresses
        self._transaction_hashes = transaction_hashes
        self._origination_addresses = origination_addresses
        self._origination_hashes = origination_hashes

        self._logger = logging.getLogger('dipdup.tzkt')

        # FIXME: Why migrations are prefetched?
        for origination in migration_originations:
            self._buffer[origination.level].append(origination)

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


class BigMapFetcher(DataFetcher[BigMapData]):
    """Fetches bigmap diffs from REST API, merges them and yields by level."""

    def __init__(
        self,
        datasource: 'TzktDatasource',
        first_level: int,
        last_level: int,
        big_map_addresses: set[str],
        big_map_paths: set[str],
    ) -> None:
        super().__init__(datasource, first_level, last_level)
        self._logger = logging.getLogger('dipdup.tzkt')
        self._big_map_addresses = big_map_addresses
        self._big_map_paths = big_map_paths

    async def fetch_by_level(self) -> AsyncGenerator[tuple[int, tuple[BigMapData, ...]], None]:
        """Iterate over big map diffs fetched fetched from REST.

        Resulting data is splitted by level, deduped, sorted and ready to be processed by BigMapIndex.
        """
        big_map_iter = self._datasource.iter_big_maps(
            self._big_map_addresses,
            self._big_map_paths,
            self._first_level,
            self._last_level,
        )
        async for level, batch in yield_by_level(big_map_iter):
            yield level, batch


class TokenTransferFetcher(DataFetcher[TokenTransferData]):
    def __init__(
        self,
        datasource: 'TzktDatasource',
        token_addresses: set[str],
        token_ids: set[int],
        from_addresses: set[str],
        to_addresses: set[str],
        first_level: int,
        last_level: int,
    ) -> None:
        super().__init__(datasource, first_level, last_level)
        self._logger = logging.getLogger('dipdup.tzkt')
        self._token_addresses = token_addresses
        self._token_ids = token_ids
        self._from_addresses = from_addresses
        self._to_addresses = to_addresses

    async def fetch_by_level(self) -> AsyncIterator[tuple[int, tuple[TokenTransferData, ...]]]:
        token_transfer_iter = self._datasource.iter_token_transfers(
            self._token_addresses,
            self._token_ids,
            self._from_addresses,
            self._to_addresses,
            self._first_level,
            self._last_level,
        )
        async for level, batch in yield_by_level(token_transfer_iter):
            yield level, batch


class EventFetcher(DataFetcher[EventData]):
    """Fetches contract events from REST API, merges them and yields by level."""

    def __init__(
        self,
        datasource: 'TzktDatasource',
        first_level: int,
        last_level: int,
        event_addresses: set[str],
        event_tags: set[str],
    ) -> None:
        self._logger = logging.getLogger('dipdup.tzkt')
        self._datasource = datasource
        self._first_level = first_level
        self._last_level = last_level
        self._event_addresses = event_addresses
        self._event_tags = event_tags

    async def fetch_by_level(self) -> AsyncGenerator[tuple[int, tuple[EventData, ...]], None]:
        """Iterate over events fetched fetched from REST.

        Resulting data is splitted by level, deduped, sorted and ready to be processed by EventIndex.
        """
        event_iter = self._datasource.iter_events(
            self._event_addresses,
            self._event_tags,
            self._first_level,
            self._last_level,
        )
        async for level, batch in yield_by_level(event_iter):
            yield level, batch
