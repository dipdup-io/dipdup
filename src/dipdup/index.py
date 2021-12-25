import logging
from abc import abstractmethod
from collections import defaultdict
from collections import deque
from collections import namedtuple
from typing import DefaultDict
from typing import Deque
from typing import Dict
from typing import Iterable
from typing import Iterator
from typing import Literal
from typing import Optional
from typing import Sequence
from typing import Set
from typing import Tuple
from typing import Union
from typing import cast

from pydantic.dataclasses import dataclass
from pydantic.error_wrappers import ValidationError

import dipdup.models as models
from dipdup.config import BigMapHandlerConfig
from dipdup.config import BigMapIndexConfig
from dipdup.config import ContractConfig
from dipdup.config import HeadHandlerConfig
from dipdup.config import HeadIndexConfig
from dipdup.config import OperationHandlerConfig
from dipdup.config import OperationHandlerOriginationPatternConfig
from dipdup.config import OperationHandlerPatternConfigT
from dipdup.config import OperationHandlerTransactionPatternConfig
from dipdup.config import OperationIndexConfig
from dipdup.config import OperationType
from dipdup.config import ResolvedIndexConfigT
from dipdup.context import DipDupContext
from dipdup.datasources.tzkt.datasource import BigMapFetcher
from dipdup.datasources.tzkt.datasource import OperationFetcher
from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.datasources.tzkt.models import deserialize_storage
from dipdup.exceptions import ConfigInitializationException
from dipdup.exceptions import InvalidDataError
from dipdup.exceptions import ReindexingReason
from dipdup.models import BigMapData
from dipdup.models import BigMapDiff
from dipdup.models import BlockData
from dipdup.models import HeadBlockData
from dipdup.models import IndexStatus
from dipdup.models import OperationData
from dipdup.models import Origination
from dipdup.models import Transaction
from dipdup.utils import FormattedLogger
from dipdup.utils.database import in_global_transaction

_logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OperationSubgroup:
    """Operations of a single contract call"""

    hash: str
    counter: int
    operations: Tuple[OperationData, ...]
    entrypoints: Set[Optional[str]]

    @property
    def length(self) -> int:
        return len(self.operations)

    def __hash__(self) -> int:
        return hash(f'{self.hash}:{self.counter}')


# NOTE: Message queue of OperationIndex
SingleLevelRollback = namedtuple('SingleLevelRollback', ('level'))
Operations = Tuple[OperationData, ...]
OperationQueueItemT = Union[Tuple[OperationSubgroup, ...], SingleLevelRollback]
OperationHandlerArgumentT = Optional[Union[Transaction, Origination, OperationData]]
MatchedOperationsT = Tuple[OperationSubgroup, OperationHandlerConfig, Deque[OperationHandlerArgumentT]]
MatchedBigMapsT = Tuple[BigMapHandlerConfig, BigMapDiff]

# NOTE: For initializing the index state on startup
block_cache: Dict[Tuple[str, int], BlockData] = {}
head_cache: DefaultDict[str, Optional[Union[models.Head, Literal[False]]]] = defaultdict(lambda: False)


def extract_operation_subgroups(
    operations: Iterable[OperationData],
    addresses: Set[str],
    entrypoints: Set[Optional[str]],
) -> Iterator[OperationSubgroup]:
    filtered: int = 0
    levels: Set[int] = set()
    operation_subgroups: DefaultDict[Tuple[str, int], Deque[OperationData]] = defaultdict(deque)

    operation_index = -1
    for operation_index, operation in enumerate(operations):
        # NOTE: Filtering out operations that are not part of any index
        if operation.type == 'transaction':
            if operation.entrypoint not in entrypoints:
                filtered += 1
                continue
            if operation.sender_address not in addresses and operation.target_address not in addresses:
                filtered += 1
                continue

        key = (operation.hash, int(operation.counter))
        operation_subgroups[key].append(operation)
        levels.add(operation.level)

    if len(levels) > 1:
        raise RuntimeError

    _logger.debug(
        'Extracted %d subgroups (%d operations, %d filtered by %s entrypoints and %s addresses)',
        len(operation_subgroups),
        operation_index + 1,
        filtered,
        len(entrypoints),
        len(addresses),
    )

    for key, operations in operation_subgroups.items():
        hash_, counter = key
        entrypoints = set(op.entrypoint for op in operations)
        yield OperationSubgroup(
            hash=hash_,
            counter=counter,
            operations=tuple(operations),
            entrypoints=entrypoints,
        )


class Index:
    """Base class for index implementations

    Provides common interface for managing index state and switching between sync and realtime modes.
    """

    _queue: Deque

    def __init__(self, ctx: DipDupContext, config: ResolvedIndexConfigT, datasource: TzktDatasource) -> None:
        self._ctx = ctx
        self._config = config
        self._datasource = datasource

        self._logger = FormattedLogger('dipdup.index', fmt=f'{config.name}: ' + '{}')
        self._state: Optional[models.Index] = None

    @property
    def datasource(self) -> TzktDatasource:
        return self._datasource

    @property
    def state(self) -> models.Index:
        if self._state is None:
            raise RuntimeError('Index state is not initialized')
        return self._state

    async def initialize_state(self, state: Optional[models.Index] = None) -> None:
        if self._state:
            raise RuntimeError('Index state is already initialized')

        if state:
            self._state = state
            return

        level = 0
        if not isinstance(self._config, HeadIndexConfig):
            level |= self._config.first_level

        self._state, _ = await models.Index.get_or_create(
            name=self._config.name,
            type=self._config.kind,
            defaults=dict(
                level=level,
                config_hash=self._config.hash(),
                template=self._config.parent.name if self._config.parent else None,
                template_values=self._config.template_values,
            ),
        )

    async def process(self) -> None:
        # NOTE: `--oneshot` flag implied
        if isinstance(self._config, (OperationIndexConfig, BigMapIndexConfig)) and self._config.last_level:
            last_level = self._config.last_level
            await self._synchronize(last_level, cache=True)
            await self.state.update_status(IndexStatus.ONESHOT, last_level)

        sync_levels = set(self.datasource.get_sync_level(s) for s in self._config.subscriptions)
        sync_level = sync_levels.pop()
        if sync_levels:
            raise Exception
        level = self.state.level

        if sync_level is None:
            raise RuntimeError('Call `set_sync_level` before starting IndexDispatcher')

        elif level < sync_level:
            self._logger.info('Index is behind datasource, sync to datasource level: %s -> %s', level, sync_level)
            self._queue.clear()
            await self._synchronize(sync_level)

        else:
            await self._process_queue()

    @abstractmethod
    async def _synchronize(self, last_level: int, cache: bool = False) -> None:
        ...

    @abstractmethod
    async def _process_queue(self) -> None:
        ...

    async def _enter_sync_state(self, last_level: int) -> Optional[int]:
        if self.state.status == IndexStatus.ONESHOT:
            return None

        first_level = self.state.level

        if first_level == last_level:
            return None
        if first_level > last_level:
            raise RuntimeError(f'Attempt to synchronize index from level {first_level} to level {last_level}')

        self._logger.info('Synchronizing index to level %s', last_level)
        await self.state.update_status(status=IndexStatus.SYNCING, level=first_level)
        return first_level

    async def _exit_sync_state(self, last_level: int) -> None:
        self._logger.info('Index is synchronized to level %s', last_level)
        await self.state.update_status(status=IndexStatus.REALTIME, level=last_level)

    def _extract_level(self, message: Union[Tuple[OperationData, ...], Tuple[BigMapData, ...]]) -> int:
        batch_levels = set(item.level for item in message)
        if len(batch_levels) != 1:
            raise RuntimeError(f'Items in operation/big_map batch have different levels: {batch_levels}')
        return batch_levels.pop()


class OperationIndex(Index):
    _config: OperationIndexConfig

    def __init__(self, ctx: DipDupContext, config: OperationIndexConfig, datasource: TzktDatasource) -> None:
        super().__init__(ctx, config, datasource)
        self._queue: Deque[OperationQueueItemT] = deque()
        self._contract_hashes: Dict[str, Tuple[int, int]] = {}
        self._rollback_level: Optional[int] = None
        self._head_hashes: Set[str] = set()
        self._migration_originations: Optional[Dict[str, OperationData]] = None

    def push_operations(self, operation_subgroups: Tuple[OperationSubgroup, ...]) -> None:
        self._queue.append(operation_subgroups)

    def push_rollback(self, level: int) -> None:
        self._queue.append(SingleLevelRollback(level))

    async def _single_level_rollback(self, level: int) -> None:
        """Ensure next arrived block has all operations of the previous block. But it could also contain additional operations.

        Called by IndexDispatcher when index datasource receive a single level rollback.
        """
        if self._rollback_level:
            raise RuntimeError('Index is already in rollback state')

        state_level = cast(int, self.state.level)
        if state_level < level:
            self._logger.info('Index level is lower than rollback level, ignoring: %s < %s', state_level, level)
        elif state_level == level:
            self._logger.info('Single level rollback, next block will be processed partially')
            self._rollback_level = level
        else:
            raise RuntimeError(f'Index level is higher than rollback level: {state_level} > {level}')

    async def _process_queue(self) -> None:
        """Process WebSocket queue"""
        while self._queue:
            message = self._queue.popleft()
            if isinstance(message, SingleLevelRollback):
                self._logger.debug('Processing rollback realtime message, %s left in queue', len(self._queue))
                await self._single_level_rollback(message.level)
            elif message:
                self._logger.debug('Processing operations realtime message, %s left in queue', len(self._queue))
                await self._process_level_operations(message)

    async def _synchronize(self, last_level: int, cache: bool = False) -> None:
        """Fetch operations via Fetcher and pass to message callback"""
        first_level = await self._enter_sync_state(last_level)
        if first_level is None:
            return

        self._logger.info('Fetching operations from level %s to %s', first_level, last_level)
        transaction_addresses = await self._get_transaction_addresses()
        origination_addresses = await self._get_origination_addresses()

        migration_originations: Tuple[OperationData, ...] = ()
        if self._config.types and OperationType.migration in self._config.types:
            migration_originations = tuple(await self._datasource.get_migration_originations(first_level))
            for op in migration_originations:
                code_hash, type_hash = await self._get_contract_hashes(cast(str, op.originated_contract_address))
                op.originated_contract_code_hash, op.originated_contract_type_hash = code_hash, type_hash

        fetcher = OperationFetcher(
            datasource=self._datasource,
            first_level=first_level,
            last_level=last_level,
            transaction_addresses=transaction_addresses,
            origination_addresses=origination_addresses,
            cache=cache,
            migration_originations=migration_originations,
        )

        async for level, operations in fetcher.fetch_operations_by_level():
            operation_subgroups = tuple(
                extract_operation_subgroups(
                    operations,
                    entrypoints=self._config.entrypoint_filter,
                    addresses=self._config.address_filter,
                )
            )
            if operation_subgroups:
                self._logger.info('Processing operations of level %s', level)
                await self._process_level_operations(operation_subgroups)

        await self._exit_sync_state(last_level)

    async def _process_level_operations(self, operation_subgroups: Tuple[OperationSubgroup, ...]) -> None:
        if not operation_subgroups:
            raise RuntimeError('No operations to process')

        level = operation_subgroups[0].operations[0].level
        if self._rollback_level:
            levels = {
                'operations': level,
                'rollback': self._rollback_level,
                'index': self.state.level,
            }
            if len(set(levels.values())) != 1:
                levels_repr = ', '.join(f'{k}={v}' for k, v in levels.items())
                raise RuntimeError(f'Index is in a rollback state, but received operation batch with different levels: {levels_repr}')

            self._logger.info('Rolling back to previous level, verifying processed operations')
            received_hashes = set(s.hash for s in operation_subgroups)
            new_hashes = received_hashes - self._head_hashes
            missing_hashes = self._head_hashes - received_hashes

            self._logger.info('Comparing hashes: %s new, %s missing', len(new_hashes), len(missing_hashes))
            if missing_hashes:
                self._logger.info('Some operations were backtracked: %s', ', '.join(missing_hashes))
                # TODO: More context
                await self._ctx.reindex(ReindexingReason.ROLLBACK)

            self._rollback_level = None
            self._head_hashes.clear()

            operation_subgroups = tuple(filter(lambda subgroup: subgroup.hash in new_hashes, operation_subgroups))

        elif level < self.state.level:
            raise RuntimeError(f'Level of operation batch must be higher than index state level: {level} < {self.state.level}')

        self._logger.debug('Processing %s operation subgroups of level %s', len(operation_subgroups), level)
        matched_handlers: Deque[MatchedOperationsT] = deque()
        for operation_subgroup in operation_subgroups:
            self._head_hashes.add(operation_subgroup.hash)
            matched_handlers += await self._match_operation_subgroup(operation_subgroup)

        # NOTE: We still need to bump index level but don't care if it will be done in existing transaction
        if not matched_handlers:
            await self.state.update_status(level=level)
            return

        async with in_global_transaction():
            for operation_subgroup, handler_config, args in matched_handlers:
                await self._call_matched_handler(handler_config, operation_subgroup, args)
            await self.state.update_status(level=level)

    async def _match_operation(self, pattern_config: OperationHandlerPatternConfigT, operation: OperationData) -> bool:
        """Match single operation with pattern"""
        # NOTE: Reversed conditions are intentional
        if isinstance(pattern_config, OperationHandlerTransactionPatternConfig):
            if pattern_config.entrypoint:
                if pattern_config.entrypoint != operation.entrypoint:
                    return False
            if pattern_config.destination:
                if pattern_config.destination_contract_config.address != operation.target_address:
                    return False
            if pattern_config.source:
                if pattern_config.source_contract_config.address != operation.sender_address:
                    return False
            return True

        elif isinstance(pattern_config, OperationHandlerOriginationPatternConfig):
            if pattern_config.source:
                if pattern_config.source_contract_config.address != operation.sender_address:
                    return False
            if pattern_config.originated_contract:
                if pattern_config.originated_contract_config.address != operation.originated_contract_address:
                    return False
            if pattern_config.similar_to:
                code_hash, type_hash = await self._get_contract_hashes(pattern_config.similar_to_contract_config.address)
                if pattern_config.strict:
                    if code_hash != operation.originated_contract_code_hash:
                        return False
                else:
                    if type_hash != operation.originated_contract_type_hash:
                        return False
            return True
        else:
            raise NotImplementedError

    async def _match_operation_subgroup(self, operation_subgroup: OperationSubgroup) -> Deque[MatchedOperationsT]:
        """Try to match operation subgroup with all patterns from indexes."""
        self._logger.debug('Matching %s', operation_subgroup)
        matched_handlers: Deque[MatchedOperationsT] = deque()
        operations = operation_subgroup.operations

        for handler_config in self._config.handlers:
            operation_idx = 0
            pattern_idx = 0
            matched_operations: Deque[Optional[OperationData]] = deque()

            # TODO: Ensure complex cases work, e.g. when optional argument is followed by required one
            # TODO: Add None to matched_operations where applicable (pattern is optional and operation not found)
            while operation_idx < len(operations):
                operation, pattern_config = operations[operation_idx], handler_config.pattern[pattern_idx]
                operation_matched = await self._match_operation(pattern_config, operation)

                if operation.type == 'origination' and isinstance(pattern_config, OperationHandlerOriginationPatternConfig):

                    if operation_matched is True and pattern_config.origination_processed(cast(str, operation.originated_contract_address)):
                        operation_matched = False

                if operation_matched:
                    matched_operations.append(operation)
                    pattern_idx += 1
                    operation_idx += 1
                elif pattern_config.optional:
                    matched_operations.append(None)
                    pattern_idx += 1
                else:
                    operation_idx += 1

                if pattern_idx == len(handler_config.pattern):
                    self._logger.info('%s: `%s` handler matched!', operation_subgroup.hash, handler_config.callback)

                    args = await self._prepare_handler_args(handler_config, matched_operations)
                    matched_handlers.append((operation_subgroup, handler_config, args))

                    matched_operations.clear()
                    pattern_idx = 0

            if len(matched_operations) >= sum(map(lambda x: 0 if x.optional else 1, handler_config.pattern)):
                self._logger.info('%s: `%s` handler matched!', operation_subgroup.hash, handler_config.callback)

                args = await self._prepare_handler_args(handler_config, matched_operations)
                matched_handlers.append((operation_subgroup, handler_config, args))

        return matched_handlers

    async def _prepare_handler_args(
        self,
        handler_config: OperationHandlerConfig,
        matched_operations: Deque[Optional[OperationData]],
    ) -> Deque[OperationHandlerArgumentT]:
        """Prepare handler arguments, parse parameter and storage."""
        args: Deque[OperationHandlerArgumentT] = deque()
        for pattern_config, operation_data in zip(handler_config.pattern, matched_operations):
            if operation_data is None:
                args.append(None)

            elif isinstance(pattern_config, OperationHandlerTransactionPatternConfig):
                if not pattern_config.entrypoint:
                    args.append(operation_data)
                    continue

                parameter_type = pattern_config.parameter_type_cls
                try:
                    parameter = parameter_type.parse_obj(operation_data.parameter_json) if parameter_type else None
                except ValidationError as e:
                    raise InvalidDataError(parameter_type, operation_data.parameter_json, operation_data) from e

                storage_type = pattern_config.storage_type_cls
                storage = deserialize_storage(operation_data, storage_type)

                transaction_context = Transaction(
                    data=operation_data,
                    parameter=parameter,
                    storage=storage,
                )
                args.append(transaction_context)

            elif isinstance(pattern_config, OperationHandlerOriginationPatternConfig):
                storage_type = pattern_config.storage_type_cls
                storage = deserialize_storage(operation_data, storage_type)

                origination_context = Origination(
                    data=operation_data,
                    storage=storage,
                )
                args.append(origination_context)

            else:
                raise NotImplementedError

        return args

    async def _call_matched_handler(
        self, handler_config: OperationHandlerConfig, operation_subgroup: OperationSubgroup, args: Sequence[OperationHandlerArgumentT]
    ) -> None:
        if not handler_config.parent:
            raise ConfigInitializationException

        await self._ctx.fire_handler(
            handler_config.callback,
            handler_config.parent.name,
            self.datasource,
            operation_subgroup.hash + ': {}',
            *args,
        )

    async def _get_transaction_addresses(self) -> Set[str]:
        """Get addresses to fetch transactions from during initial synchronization"""
        if OperationType.transaction not in self._config.types:
            return set()
        return set(contract.address for contract in self._config.contracts if isinstance(contract, ContractConfig))

    async def _get_origination_addresses(self) -> Set[str]:
        """Get addresses to fetch origination from during initial synchronization"""
        addresses = set()
        for handler_config in self._config.handlers:
            for pattern_config in handler_config.pattern:
                if isinstance(pattern_config, OperationHandlerOriginationPatternConfig):
                    if pattern_config.originated_contract:
                        addresses.add(pattern_config.originated_contract_config.address)
                    if pattern_config.source:
                        for address in await self._datasource.get_originated_contracts(pattern_config.source_contract_config.address):
                            addresses.add(address)
                    if pattern_config.similar_to:
                        for address in await self._datasource.get_similar_contracts(
                            address=pattern_config.similar_to_contract_config.address,
                            strict=pattern_config.strict,
                        ):
                            addresses.add(address)
        return addresses

    async def _get_contract_hashes(self, address: str) -> Tuple[int, int]:
        if address not in self._contract_hashes:
            summary = await self._datasource.get_contract_summary(address)
            self._contract_hashes[address] = (summary['codeHash'], summary['typeHash'])
        return self._contract_hashes[address]


class BigMapIndex(Index):
    _config: BigMapIndexConfig

    def __init__(self, ctx: DipDupContext, config: BigMapIndexConfig, datasource: TzktDatasource) -> None:
        super().__init__(ctx, config, datasource)
        self._queue: Deque[Tuple[BigMapData, ...]] = deque()

    def push_big_maps(self, big_maps: Tuple[BigMapData, ...]) -> None:
        self._queue.append(big_maps)

    async def _process_queue(self) -> None:
        """Process WebSocket queue"""
        if self._queue:
            self._logger.debug('Processing websocket queue')
        while self._queue:
            big_maps = self._queue.popleft()
            await self._process_level_big_maps(big_maps)

    async def _synchronize(self, last_level: int, cache: bool = False) -> None:
        """Fetch operations via Fetcher and pass to message callback"""
        first_level = await self._enter_sync_state(last_level)
        if first_level is None:
            return

        self._logger.info('Fetching big map diffs from level %s to %s', first_level, last_level)

        big_map_addresses = await self._get_big_map_addresses()
        big_map_paths = await self._get_big_map_paths()

        fetcher = BigMapFetcher(
            datasource=self._datasource,
            first_level=first_level,
            last_level=last_level,
            big_map_addresses=big_map_addresses,
            big_map_paths=big_map_paths,
            cache=cache,
        )

        async for _, big_maps in fetcher.fetch_big_maps_by_level():
            await self._process_level_big_maps(big_maps)

        await self._exit_sync_state(last_level)

    async def _process_level_big_maps(self, big_maps: Tuple[BigMapData, ...]):
        if not big_maps:
            return
        level = self._extract_level(big_maps)

        # NOTE: le operator because single level rollbacks are not supported
        if level <= self.state.level:
            raise RuntimeError(f'Level of big map batch must be higher than index state level: {level} <= {self.state.level}')

        self._logger.debug('Processing big map diffs of level %s', level)
        matched_handlers = await self._match_big_maps(big_maps)

        # NOTE: We still need to bump index level but don't care if it will be done in existing transaction
        if not matched_handlers:
            await self.state.update_status(level=level)
            return

        async with in_global_transaction():
            for handler_config, big_map_diff in matched_handlers:
                await self._call_matched_handler(handler_config, big_map_diff)
            await self.state.update_status(level=level)

    async def _match_big_map(self, handler_config: BigMapHandlerConfig, big_map: BigMapData) -> bool:
        """Match single big map diff with pattern"""
        if handler_config.path != big_map.path:
            return False
        if handler_config.contract_config.address != big_map.contract_address:
            return False
        return True

    async def _prepare_handler_args(
        self,
        handler_config: BigMapHandlerConfig,
        matched_big_map: BigMapData,
    ) -> BigMapDiff:
        """Prepare handler arguments, parse key and value. Schedule callback in executor."""
        self._logger.info('%s: `%s` handler matched!', matched_big_map.operation_id, handler_config.callback)
        if not handler_config.parent:
            raise ConfigInitializationException

        if matched_big_map.action.has_key:
            key_type = handler_config.key_type_cls
            try:
                key = key_type.parse_obj(matched_big_map.key)
            except ValidationError as e:
                raise InvalidDataError(key_type, matched_big_map.key, matched_big_map) from e
        else:
            key = None

        if matched_big_map.action.has_value:
            value_type = handler_config.value_type_cls
            try:
                value = value_type.parse_obj(matched_big_map.value)
            except ValidationError as e:
                raise InvalidDataError(value_type, matched_big_map.key, matched_big_map) from e
        else:
            value = None

        return BigMapDiff(
            data=matched_big_map,
            action=matched_big_map.action,
            key=key,
            value=value,
        )

    async def _match_big_maps(self, big_maps: Iterable[BigMapData]) -> Deque[MatchedBigMapsT]:
        """Try to match big map diffs in cache with all patterns from indexes."""
        matched_handlers: Deque[MatchedBigMapsT] = deque()

        for big_map in big_maps:
            for handler_config in self._config.handlers:
                big_map_matched = await self._match_big_map(handler_config, big_map)
                if big_map_matched:
                    arg = await self._prepare_handler_args(handler_config, big_map)
                    matched_handlers.append((handler_config, arg))

        return matched_handlers

    async def _call_matched_handler(self, handler_config: BigMapHandlerConfig, big_map_diff: BigMapDiff) -> None:
        if not handler_config.parent:
            raise ConfigInitializationException

        await self._ctx.fire_handler(
            handler_config.callback,
            handler_config.parent.name,
            self.datasource,
            # FIXME: missing `operation_id` field in API to identify operation
            None,
            big_map_diff,
        )

    async def _get_big_map_addresses(self) -> Set[str]:
        """Get addresses to fetch big map diffs from during initial synchronization"""
        addresses = set()
        for handler_config in self._config.handlers:
            addresses.add(cast(ContractConfig, handler_config.contract).address)
        return addresses

    async def _get_big_map_paths(self) -> Set[str]:
        """Get addresses to fetch big map diffs from during initial synchronization"""
        paths = set()
        for handler_config in self._config.handlers:
            paths.add(handler_config.path)
        return paths


class HeadIndex(Index):
    _config: HeadIndexConfig

    def __init__(self, ctx: DipDupContext, config: HeadIndexConfig, datasource: TzktDatasource) -> None:
        super().__init__(ctx, config, datasource)
        self._queue: Deque[HeadBlockData] = deque()

    async def _synchronize(self, last_level: int, cache: bool = False) -> None:
        self._logger.info('Setting index level to %s and moving on', last_level)
        await self.state.update_status(status=IndexStatus.REALTIME, level=last_level)

    async def _process_queue(self) -> None:
        while self._queue:
            head = self._queue.popleft()
            self._logger.debug('Processing head realtime message, %s left in queue', len(self._queue))

            level = head.level
            if level <= self.state.level:
                raise RuntimeError(f'Level of head must be higher than index state level: {level} <= {self.state.level}')

            async with in_global_transaction():
                self._logger.debug('Processing head info of level %s', level)
                for handler_config in self._config.handlers:
                    await self._call_matched_handler(handler_config, head)
                await self.state.update_status(level=level)

    async def _call_matched_handler(self, handler_config: HeadHandlerConfig, head: HeadBlockData) -> None:
        if not handler_config.parent:
            raise ConfigInitializationException

        await self._ctx.fire_handler(
            handler_config.callback,
            handler_config.parent.name,
            self.datasource,
            head.hash,
            head,
        )

    def push_head(self, head: HeadBlockData) -> None:
        self._queue.append(head)
