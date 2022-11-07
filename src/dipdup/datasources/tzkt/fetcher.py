import logging
from abc import ABC
from abc import abstractmethod
from collections import defaultdict
from collections import deque
from enum import Enum
from typing import TYPE_CHECKING
from typing import AsyncGenerator
from typing import AsyncIterator
from typing import Generic
from typing import Protocol
from typing import TypeVar

from dipdup.models import BigMapData
from dipdup.models import EventData
from dipdup.models import OperationData
from dipdup.models import TokenTransferData

if TYPE_CHECKING:
    from dipdup.datasources.tzkt.datasource import TzktDatasource


class OperationFetcherRequest(Enum):
    """Represents multiple TzKT calls to be merged into a single batch of operations"""

    sender_transactions = 'sender_transactions'
    target_transactions = 'target_transactions'
    originations = 'originations'


class HasLevel(Protocol):
    level: int


HasLevelT = TypeVar('HasLevelT', bound=HasLevel)


async def yield_by_level(
    iterable: AsyncIterator[tuple[HasLevelT, ...]]
) -> AsyncGenerator[tuple[int, tuple[HasLevelT, ...]], None]:
    items: tuple[HasLevelT, ...] = ()

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


class DataFetcher(Generic[HasLevelT], ABC):
    @abstractmethod
    def fetch_by_level(self) -> AsyncIterator[tuple[int, tuple[HasLevelT, ...]]]:
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
        origination_addresses: set[str],
        migration_originations: tuple[OperationData, ...] = (),
    ) -> None:
        self._datasource = datasource
        self._first_level = first_level
        self._last_level = last_level
        self._transaction_addresses = transaction_addresses
        self._origination_addresses = origination_addresses

        self._logger = logging.getLogger('dipdup.tzkt')
        self._head: int = 0
        self._heads: dict[OperationFetcherRequest, int] = {}
        self._offsets: dict[OperationFetcherRequest, int] = {}
        self._fetched: dict[OperationFetcherRequest, bool] = {}

        self._operations: defaultdict[int, deque[OperationData]] = defaultdict(deque)
        for origination in migration_originations:
            self._operations[origination.level].append(origination)

    def _get_operations_head(self, operations: tuple[OperationData, ...]) -> int:
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

        # FIXME: No pagination because of URL length limit workaround
        originations = await self._datasource.get_originations(
            addresses=self._origination_addresses,
            first_level=self._first_level,
            last_level=self._last_level,
        )

        for op in originations:
            level = op.level
            self._operations[level].append(op)

        self._logger.debug('Got %s', len(originations))
        self._fetched[key] = True
        self._heads[key] = self._last_level

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
        )

        for op in transactions:
            level = op.level
            self._operations[level].append(op)

        self._logger.debug('Got %s', len(transactions))

        if len(transactions) < self._datasource.request_limit:
            self._fetched[key] = True
            self._heads[key] = self._last_level
        else:
            self._offsets[key] = transactions[-1].id
            self._heads[key] = self._get_operations_head(transactions)

    @staticmethod
    def dedup_operations(operations: tuple[OperationData, ...]) -> tuple[OperationData, ...]:
        """Merge and sort operations fetched from multiple endpoints"""
        return tuple(
            sorted(
                (({op.id: op for op in operations}).values()),
                key=lambda op: op.id,
            )
        )

    async def fetch_by_level(self) -> AsyncIterator[tuple[int, tuple[OperationData, ...]]]:
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
                    yield self._head, self.dedup_operations(tuple(operations))
                self._head += 1

            if all(self._fetched.values()):
                break

        if self._operations:
            raise RuntimeError('Operations left in queue')


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
        self._logger = logging.getLogger('dipdup.tzkt')
        self._datasource = datasource
        self._first_level = first_level
        self._last_level = last_level
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
        self._logger = logging.getLogger('dipdup.tzkt')
        self._datasource = datasource
        self._token_addresses = token_addresses
        self._token_ids = token_ids
        self._from_addresses = from_addresses
        self._to_addresses = to_addresses
        self._first_level = first_level
        self._last_level = last_level

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
