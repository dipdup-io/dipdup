import logging
from collections import defaultdict
from collections import deque
from collections.abc import Coroutine
from collections.abc import Iterable
from collections.abc import Iterator
from collections.abc import Sequence
from typing import Any

from dipdup.config.tezos_tzkt_operations import OperationsHandlerOriginationPatternConfig as OriginationPatternConfig
from dipdup.config.tezos_tzkt_operations import (
    OperationsHandlerSmartRollupExecutePatternConfig as SmartRollupExecutePatternConfig,
)
from dipdup.config.tezos_tzkt_operations import OperationsHandlerTransactionPatternConfig as TransactionPatternConfig
from dipdup.config.tezos_tzkt_operations import TzktOperationsHandlerConfig
from dipdup.config.tezos_tzkt_operations import TzktOperationsHandlerConfigU
from dipdup.config.tezos_tzkt_operations import TzktOperationsIndexConfig
from dipdup.config.tezos_tzkt_operations import TzktOperationsIndexConfigU
from dipdup.config.tezos_tzkt_operations import TzktOperationsUnfilteredIndexConfig
from dipdup.context import DipDupContext
from dipdup.datasources.tezos_tzkt import TzktDatasource
from dipdup.exceptions import ConfigInitializationException
from dipdup.exceptions import FrameworkException
from dipdup.indexes.tezos_tzkt import TzktIndex
from dipdup.indexes.tezos_tzkt_operations.fetcher import OperationFetcher
from dipdup.indexes.tezos_tzkt_operations.fetcher import OperationUnfilteredFetcher
from dipdup.indexes.tezos_tzkt_operations.matcher import MatchedOperationsT
from dipdup.indexes.tezos_tzkt_operations.matcher import OperationsHandlerArgumentU
from dipdup.indexes.tezos_tzkt_operations.matcher import OperationSubgroup
from dipdup.indexes.tezos_tzkt_operations.matcher import match_operation_subgroup
from dipdup.indexes.tezos_tzkt_operations.matcher import match_operation_unfiltered_subgroup
from dipdup.models.tezos_tzkt import TzktMessageType
from dipdup.models.tezos_tzkt import TzktOperationData
from dipdup.models.tezos_tzkt import TzktRollbackMessage
from dipdup.prometheus import Metrics

_logger = logging.getLogger('dipdup.matcher')

OperationQueueItem = tuple[OperationSubgroup, ...] | TzktRollbackMessage


def entrypoint_filter(handlers: tuple[TzktOperationsHandlerConfig, ...]) -> set[str | None]:
    """Set of entrypoints to filter operations with before an actual matching"""
    entrypoints = set()
    for handler_config in handlers:
        for pattern_config in handler_config.pattern:
            if not isinstance(pattern_config, TransactionPatternConfig):
                continue
            entrypoints.add(pattern_config.entrypoint)

    return entrypoints


def address_filter(handlers: tuple[TzktOperationsHandlerConfig, ...]) -> set[str]:
    """Set of addresses (any field) to filter operations with before an actual matching"""
    addresses = set()
    for handler_config in handlers:
        for pattern_config in handler_config.pattern:
            if isinstance(pattern_config, TransactionPatternConfig):
                if pattern_config.source:
                    if address := pattern_config.source.address:
                        addresses.add(address)
                if pattern_config.destination:
                    if address := pattern_config.destination.address:
                        addresses.add(address)
            elif isinstance(pattern_config, OriginationPatternConfig):
                if pattern_config.originated_contract:
                    if address := pattern_config.originated_contract.address:
                        addresses.add(address)
            elif isinstance(pattern_config, SmartRollupExecutePatternConfig):
                if pattern_config.destination:
                    if address := pattern_config.destination.address:
                        addresses.add(address)

    return addresses


def code_hash_filter(handlers: tuple[TzktOperationsHandlerConfig, ...]) -> set[int]:
    """Set of code hashes to filter operations with before an actual matching"""
    code_hashes: set[int] = set()
    for handler_config in handlers:
        for pattern_config in handler_config.pattern:
            if isinstance(pattern_config, TransactionPatternConfig):
                if pattern_config.source:
                    if code_hash := pattern_config.source.resolved_code_hash:
                        code_hashes.add(code_hash)
                if pattern_config.destination:
                    if code_hash := pattern_config.destination.resolved_code_hash:
                        code_hashes.add(code_hash)
            elif isinstance(pattern_config, OriginationPatternConfig):
                if pattern_config.source:
                    if code_hash := pattern_config.source.resolved_code_hash:
                        raise FrameworkException('`source.code_hash` is not supported for origination patterns')

                if pattern_config.originated_contract:
                    if code_hash := pattern_config.originated_contract.resolved_code_hash:
                        code_hashes.add(code_hash)

    return code_hashes


def extract_operation_subgroups(
    operations: Iterable[TzktOperationData],
    addresses: set[str],
    entrypoints: set[str | None],
    code_hashes: set[int],
) -> Iterator[OperationSubgroup]:
    filtered: int = 0
    levels: set[int] = set()
    operation_subgroups: defaultdict[tuple[str, int], deque[TzktOperationData]] = defaultdict(deque)

    _operation_index = -1
    for _operation_index, op in enumerate(operations):
        # NOTE: Filtering out operations that are not part of any index
        if op.type == 'transaction':
            if entrypoints and op.entrypoint not in entrypoints:
                filtered += 1
                continue

            wrong_address = addresses and not {op.sender_address, op.target_address} & addresses
            wrong_code_hash = code_hashes and not {op.sender_code_hash, op.target_code_hash} & code_hashes
            if wrong_address and wrong_code_hash:
                filtered += 1
                continue

        key = (op.hash, int(op.counter))
        operation_subgroups[key].append(op)
        levels.add(op.level)

    if len(levels) > 1:
        raise FrameworkException('Operations in batch are not in the same level')

    _logger.debug(
        'Extracted %d subgroups (%d operations, %d filtered by %s entrypoints and %s addresses)',
        len(operation_subgroups),
        _operation_index + 1,
        filtered,
        len(entrypoints),
        len(addresses),
    )

    for key, operations in operation_subgroups.items():
        hash_, counter = key
        entrypoints = {op.entrypoint for op in operations}
        yield OperationSubgroup(
            hash=hash_,
            counter=counter,
            operations=tuple(operations),
            entrypoints=entrypoints,
        )


class TzktOperationsIndex(
    TzktIndex[TzktOperationsIndexConfigU, OperationQueueItem],
    message_type=TzktMessageType.operation,
):
    def __init__(
        self,
        ctx: DipDupContext,
        config: TzktOperationsIndexConfigU,
        datasource: TzktDatasource,
    ) -> None:
        super().__init__(ctx, config, datasource)
        self._entrypoint_filter: set[str | None] = set()
        self._address_filter: set[str] = set()
        self._code_hash_filter: set[int] = set()

    def push_operations(self, operation_subgroups: OperationQueueItem) -> None:
        self.push_realtime_message(operation_subgroups)

    async def get_filters(self) -> tuple[set[str | None], set[str], set[int]]:
        if isinstance(self._config, TzktOperationsUnfilteredIndexConfig):
            return set(), set(), set()

        if self._entrypoint_filter or self._address_filter or self._code_hash_filter:
            return self._entrypoint_filter, self._address_filter, self._code_hash_filter

        for code_hash in code_hash_filter(self._config.handlers):
            self._code_hash_filter.add(code_hash)

        self._entrypoint_filter = entrypoint_filter(self._config.handlers)
        self._address_filter = address_filter(self._config.handlers)

        return self._entrypoint_filter, self._address_filter, self._code_hash_filter

    # FIXME: Use method from TzktIndex
    async def _process_queue(self) -> None:
        """Process WebSocket queue"""
        self._logger.debug('Processing %s realtime messages from queue', len(self._queue))

        while self._queue:
            message = self._queue.popleft()
            if isinstance(message, TzktRollbackMessage):
                await self._tzkt_rollback(message.from_level, message.to_level)
                continue

            messages_left = len(self._queue)
            Metrics.set_levels_to_realtime(self._config.name, messages_left)

            message_level = message[0].operations[0].level

            if message_level <= self.state.level:
                self._logger.debug('Skipping outdated message: %s <= %s', message_level, self.state.level)
                continue

            await self._process_level_operations(message, message_level)

        else:
            Metrics.set_levels_to_realtime(self._config.name, 0)

    async def _create_fetcher(self, first_level: int, sync_level: int) -> OperationFetcher | OperationUnfilteredFetcher:
        if isinstance(self._config, TzktOperationsIndexConfig):
            return await OperationFetcher.create(
                self._config,
                self._datasource,
                first_level,
                sync_level,
            )
        if isinstance(self._config, TzktOperationsUnfilteredIndexConfig):
            return await OperationUnfilteredFetcher.create(
                self._config,
                self._datasource,
                first_level,
                sync_level,
            )
        raise NotImplementedError

    async def _synchronize(self, sync_level: int) -> None:
        """Fetch operations via Fetcher and pass to message callback"""
        index_level = await self._enter_sync_state(sync_level)
        if index_level is None:
            return

        first_level = index_level + 1
        self._logger.info('Fetching operations from level %s to %s', first_level, sync_level)

        fetcher = await self._create_fetcher(first_level, sync_level)

        async for level, operations in fetcher.fetch_by_level():
            Metrics.set_levels_to_sync(self._config.name, sync_level - level)

            operation_subgroups = tuple(
                extract_operation_subgroups(
                    operations,
                    entrypoints=self._entrypoint_filter,
                    addresses=self._address_filter,
                    code_hashes=self._code_hash_filter,
                )
            )
            if operation_subgroups:
                self._logger.debug('Processing operations of level %s', level)
                await self._process_level_operations(operation_subgroups, sync_level)

        await self._exit_sync_state(sync_level)

    # FIXME: Use method from TzktIndex
    async def _process_level_operations(
        self,
        operation_subgroups: tuple[OperationSubgroup, ...],
        sync_level: int,
    ) -> None:
        if not operation_subgroups:
            return

        batch_level = operation_subgroups[0].operations[0].level
        index_level = self.state.level
        if batch_level <= index_level:
            raise FrameworkException(f'Batch level is lower than index level: {batch_level} <= {index_level}')

        self._logger.debug('Processing %s operation subgroups of level %s', len(operation_subgroups), batch_level)
        matched_handlers: deque[MatchedOperationsT] = deque()
        for operation_subgroup in operation_subgroups:
            if isinstance(self._config, TzktOperationsUnfilteredIndexConfig):
                subgroup_handlers = match_operation_unfiltered_subgroup(
                    index=self._config,
                    operation_subgroup=operation_subgroup,
                )
            else:
                subgroup_handlers = match_operation_subgroup(
                    self._ctx.package,
                    handlers=self._config.handlers,
                    operation_subgroup=operation_subgroup,
                    alt=self._ctx.config.advanced.alt_operation_matcher,
                )

            if subgroup_handlers:
                self._logger.debug(
                    '%s: `%s` handler matched!',
                    operation_subgroup.hash,
                    subgroup_handlers[0][1].callback,
                )
            matched_handlers += subgroup_handlers

        Metrics.set_index_handlers_matched(len(matched_handlers))

        # NOTE: We still need to bump index level but don't care if it will be done in existing transaction
        if not matched_handlers:
            await self._update_state(level=batch_level)
            return

        async with self._ctx.transactions.in_transaction(batch_level, sync_level, self.name):
            for operation_subgroup, handler_config, args in matched_handlers:
                await self._call_matched_handler(handler_config, (operation_subgroup, args))
            await self._update_state(level=batch_level)

    async def _call_matched_handler(
        self,
        handler_config: TzktOperationsHandlerConfigU,
        level_data: tuple[OperationSubgroup, Sequence[OperationsHandlerArgumentU]],
    ) -> None:
        operation_subgroup, args = level_data
        if not handler_config.parent:
            raise ConfigInitializationException

        await self._ctx.fire_handler(
            handler_config.callback,
            handler_config.parent.name,
            self.datasource,
            operation_subgroup.hash + ': {}',
            *args,
        )

    def _match_level_data(self, handlers: Any, level_data: Any) -> deque[Any]:
        raise NotImplementedError

    def _process_level_data(self, level_data: OperationQueueItem, sync_level: int) -> Coroutine[Any, Any, None]:
        raise NotImplementedError
