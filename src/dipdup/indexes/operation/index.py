import logging
from collections import defaultdict
from collections import deque
from contextlib import ExitStack
from typing import Iterable
from typing import Iterator
from typing import Sequence

from dipdup.config import OperationHandlerConfig
from dipdup.config import OperationHandlerOriginationPatternConfig as OriginationPatternConfig
from dipdup.config import OperationHandlerTransactionPatternConfig as TransactionPatternConfig
from dipdup.config import OperationIndexConfig
from dipdup.context import DipDupContext
from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.enums import MessageType
from dipdup.exceptions import ConfigInitializationException
from dipdup.exceptions import FrameworkException
from dipdup.index import Index
from dipdup.indexes.operation.fetcher import OperationFetcher
from dipdup.indexes.operation.matcher import MatchedOperationsT
from dipdup.indexes.operation.matcher import OperationHandlerArgumentT
from dipdup.indexes.operation.matcher import OperationSubgroup
from dipdup.indexes.operation.matcher import match_operation_subgroup
from dipdup.models import OperationData
from dipdup.prometheus import Metrics

_logger = logging.getLogger('dipdup_matcher')

OperationQueueItem = tuple[OperationSubgroup, ...]


def entrypoint_filter(handlers: tuple[OperationHandlerConfig, ...]) -> set[str | None]:
    """Set of entrypoints to filter operations with before an actual matching"""
    entrypoints = set()
    for handler_config in handlers:
        for pattern_config in handler_config.pattern:
            if not isinstance(pattern_config, TransactionPatternConfig):
                continue
            entrypoints.add(pattern_config.entrypoint)

    return entrypoints


def address_filter(handlers: tuple[OperationHandlerConfig, ...]) -> set[str]:
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
                # TODO: Remove in 7.0
                if pattern_config.similar_to:
                    raise FrameworkException('originated_contract` alias, should be replaced in __init__')

                if pattern_config.originated_contract:
                    if address := pattern_config.originated_contract.address:
                        addresses.add(address)

    return addresses


def code_hash_filter(handlers: tuple[OperationHandlerConfig, ...]) -> set[int | str]:
    """Set of code hashes to filter operations with before an actual matching"""
    code_hashes = set()
    for handler_config in handlers:
        for pattern_config in handler_config.pattern:
            if isinstance(pattern_config, TransactionPatternConfig):
                if pattern_config.source:
                    if code_hash := pattern_config.source.code_hash:
                        code_hashes.add(code_hash)
                if pattern_config.destination:
                    if code_hash := pattern_config.destination.code_hash:
                        code_hashes.add(code_hash)
            elif isinstance(pattern_config, OriginationPatternConfig):
                # TODO: Remove in 7.0
                if pattern_config.similar_to:
                    raise FrameworkException('originated_contract` alias, should be replaced in __init__')

                if pattern_config.source:
                    if code_hash := pattern_config.source.code_hash:
                        raise FrameworkException('`source.code_hash` is not supported for origination patterns')

                if pattern_config.originated_contract:
                    if code_hash := pattern_config.originated_contract.code_hash:
                        code_hashes.add(code_hash)

    return code_hashes


def extract_operation_subgroups(
    operations: Iterable[OperationData],
    addresses: set[str],
    entrypoints: set[str | None],
    code_hashes: set[int],
) -> Iterator[OperationSubgroup]:
    filtered: int = 0
    levels: set[int] = set()
    operation_subgroups: defaultdict[tuple[str, int], deque[OperationData]] = defaultdict(deque)

    _operation_index = -1
    for _operation_index, operation in enumerate(operations):
        # NOTE: Filtering out operations that are not part of any index
        if operation.type == 'transaction':
            if entrypoints and operation.entrypoint not in entrypoints:
                filtered += 1
                continue
            if addresses and operation.sender_address not in addresses and operation.target_address not in addresses:
                filtered += 1
                continue
            if (
                code_hashes
                and operation.target_code_hash not in code_hashes
                and operation.sender_code_hash not in code_hashes
            ):
                filtered += 1
                continue

        key = (operation.hash, int(operation.counter))
        operation_subgroups[key].append(operation)
        levels.add(operation.level)

    if len(levels) > 1:
        raise RuntimeError('Operations in batch are not in the same level')

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


class OperationIndex(
    Index[OperationIndexConfig, OperationQueueItem, TzktDatasource],
    message_type=MessageType.operation,
):
    def __init__(self, ctx: DipDupContext, config: OperationIndexConfig, datasource: TzktDatasource) -> None:
        super().__init__(ctx, config, datasource)
        self._entrypoint_filter: set[str | None] = set()
        self._address_filter: set[str] = set()
        self._code_hash_filter: set[int] = set()

    def push_operations(self, operation_subgroups: OperationQueueItem) -> None:
        self.push_realtime_message(operation_subgroups)

    async def get_filters(self) -> tuple[set[str | None], set[str], set[int]]:
        if self._entrypoint_filter or self._address_filter or self._code_hash_filter:
            return self._entrypoint_filter, self._address_filter, self._code_hash_filter

        for code_hash in code_hash_filter(self._config.handlers):
            if not isinstance(code_hash, int):
                code_hash, _ = await self._datasource.get_contract_hashes(code_hash)
            self._code_hash_filter.add(code_hash)

        self._entrypoint_filter = entrypoint_filter(self._config.handlers)
        self._address_filter = address_filter(self._config.handlers)

        return self._entrypoint_filter, self._address_filter, self._code_hash_filter

    async def _process_queue(self) -> None:
        """Process WebSocket queue"""
        self._logger.debug('Processing %s realtime messages from queue', len(self._queue))

        while self._queue:
            message = self._queue.popleft()
            messages_left = len(self._queue)

            if not message:
                raise FrameworkException('Got empty message from realtime queue')

            if Metrics.enabled:
                Metrics.set_levels_to_realtime(self._config.name, messages_left)

            message_level = message[0].operations[0].level

            if message_level <= self.state.level:
                self._logger.debug('Skipping outdated message: %s <= %s', message_level, self.state.level)
                continue

            with ExitStack() as stack:
                if Metrics.enabled:
                    stack.enter_context(Metrics.measure_level_realtime_duration())
                await self._process_level_operations(message, message_level)

        else:
            if Metrics.enabled:
                Metrics.set_levels_to_realtime(self._config.name, 0)

    async def _synchronize(self, sync_level: int) -> None:
        """Fetch operations via Fetcher and pass to message callback"""
        index_level = await self._enter_sync_state(sync_level)
        if index_level is None:
            return

        first_level = index_level + 1
        self._logger.info('Fetching operations from level %s to %s', first_level, sync_level)
        fetcher = await OperationFetcher.create(
            self._config,
            self._datasource,
            first_level,
            sync_level,
        )

        async for level, operations in fetcher.fetch_by_level():
            if Metrics.enabled:
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
                self._logger.info('Processing operations of level %s', level)
                with ExitStack() as stack:
                    if Metrics.enabled:
                        stack.enter_context(Metrics.measure_level_sync_duration())
                    await self._process_level_operations(operation_subgroups, sync_level)

        await self._exit_sync_state(sync_level)

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
            subgroup_handlers = match_operation_subgroup(
                self._config.handlers,
                operation_subgroup,
            )
            if subgroup_handlers:
                self._logger.info(
                    '%s: `%s` handler matched!',
                    operation_subgroup.hash,
                    subgroup_handlers[0][1].callback,
                )
            matched_handlers += subgroup_handlers

        if Metrics.enabled:
            Metrics.set_index_handlers_matched(len(matched_handlers))

        # NOTE: We still need to bump index level but don't care if it will be done in existing transaction
        if not matched_handlers:
            await self.state.update_status(level=batch_level)
            return

        async with self._ctx._transactions.in_transaction(batch_level, sync_level, self.name):
            for operation_subgroup, handler_config, args in matched_handlers:
                await self._call_matched_handler(handler_config, operation_subgroup, args)
            await self.state.update_status(level=batch_level)

    async def _call_matched_handler(
        self,
        handler_config: OperationHandlerConfig,
        operation_subgroup: OperationSubgroup,
        args: Sequence[OperationHandlerArgumentT],
    ) -> None:
        if not handler_config.parent:
            raise ConfigInitializationException

        await self._ctx._fire_handler(
            handler_config.callback,
            handler_config.parent.name,
            self.datasource,
            operation_subgroup.hash + ': {}',
            *args,
        )
