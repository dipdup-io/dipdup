from abc import abstractmethod
from collections import defaultdict, deque, namedtuple
from contextlib import suppress
from typing import Deque, Dict, List, Optional, Set, Tuple, Union, cast

from pydantic.error_wrappers import ValidationError

from dipdup.config import (
    BigMapHandlerConfig,
    BigMapIndexConfig,
    ContractConfig,
    IndexConfigTemplateT,
    OperationHandlerConfig,
    OperationHandlerOriginationPatternConfig,
    OperationHandlerPatternConfigT,
    OperationHandlerTransactionPatternConfig,
    OperationIndexConfig,
    OperationType,
)
from dipdup.context import DipDupContext, HandlerContext
from dipdup.datasources.tzkt.datasource import BigMapFetcher, OperationFetcher, TzktDatasource
from dipdup.exceptions import InvalidDataError
from dipdup.models import BigMapData, BigMapDiff, HeadBlockData, OperationData, Origination, State, TemporaryState, Transaction
from dipdup.utils import FormattedLogger, in_global_transaction

# NOTE: Operations of a single contract call
OperationSubgroup = namedtuple('OperationSubgroup', ('hash', 'counter'))


class Index:
    _queue: Deque

    def __init__(self, ctx: DipDupContext, config: IndexConfigTemplateT, datasource: TzktDatasource) -> None:
        self._ctx = ctx
        self._config = config
        self._datasource = datasource

        self._logger = FormattedLogger('dipdup.index', fmt=f'{config.name}: ' + '{}')
        self._state: Optional[State] = None

    @property
    def datasource(self) -> TzktDatasource:
        return self._datasource

    async def get_state(self) -> State:
        """Get state of index containing current level and config hash"""
        if self._state is None:
            await self._initialize_index_state()
        return cast(State, self._state)

    async def process(self) -> None:
        state = await self.get_state()
        if self._config.last_block:
            last_level = self._config.last_block
            await self._synchronize(last_level, cache=True)
        elif self._datasource.sync_level is None:
            self._logger.info('Datasource is not active, sync to the latest block')
            last_level = (await self._datasource.get_head_block()).level
            await self._synchronize(last_level)
        elif self._datasource.sync_level > state.level:
            self._logger.info('Index is behind datasource, sync to datasource level')
            self._queue.clear()
            last_level = self._datasource.sync_level
            await self._synchronize(last_level)
        else:
            await self._process_queue()

    @abstractmethod
    async def _synchronize(self, last_level: int, cache: bool = False) -> None:
        ...

    @abstractmethod
    async def _process_queue(self) -> None:
        ...

    async def _enter_sync_state(self, last_level: int) -> Optional[int]:
        state = await self.get_state()
        first_level = state.level
        if first_level == last_level:
            return None
        if first_level > last_level:
            raise RuntimeError(f'Attempt to synchronize index from level {first_level} to level {last_level}')
        self._logger.info('Synchronizing index to level %s', last_level)
        state.hash = None  # type: ignore
        await state.save()
        return first_level

    async def _exit_sync_state(self, last_level: int) -> None:
        self._logger.info('Index is synchronized to level %s', last_level)
        state = await self.get_state()
        state.level = last_level  # type: ignore
        await state.save()

    async def _initialize_index_state(self) -> None:
        self._logger.info('Getting index state')
        index_config_hash = self._config.hash()
        state = await State.get_or_none(
            index_name=self._config.name,
            index_type=self._config.kind,
        )
        if state is None:
            state_cls = TemporaryState if self._config.stateless else State
            state = state_cls(
                index_name=self._config.name,
                index_type=self._config.kind,
                index_hash=index_config_hash,
                level=self._config.first_block,
            )

        elif state.index_hash != index_config_hash:
            self._logger.warning('Config hash mismatch (config has been changed), reindexing')
            await self._ctx.reindex()

        self._logger.info('%s', f'{state.level=} {state.hash=}'.replace('state.', ''))
        # NOTE: No need to check indexes which are not synchronized.
        if state.level and state.hash:
            block = await self._datasource.get_block(state.level)
            if state.hash != block.hash:
                self._logger.warning('Block hash mismatch (missed rollback while dipdup was stopped), reindexing')
                await self._ctx.reindex()

        await state.save()
        self._state = state


class OperationIndex(Index):
    _config: OperationIndexConfig

    def __init__(self, ctx: DipDupContext, config: OperationIndexConfig, datasource: TzktDatasource) -> None:
        super().__init__(ctx, config, datasource)
        self._queue: Deque[Tuple[int, List[OperationData], Optional[HeadBlockData]]] = deque()
        self._contract_hashes: Dict[str, Tuple[int, int]] = {}
        self._rollback_level: Optional[int] = None
        self._last_hashes: Set[str] = set()
        self._migration_originations: Optional[Dict[str, OperationData]] = None

    def push(self, level: int, operations: List[OperationData], block: Optional[HeadBlockData] = None) -> None:
        self._queue.append((level, operations, block))

    async def single_level_rollback(self, from_level: int) -> None:
        """Ensure next arrived block is the same as rolled back one"""
        self._rollback_level = from_level

    async def _process_queue(self) -> None:
        if not self._queue:
            return
        self._logger.info('Processing websocket queue')
        with suppress(IndexError):
            while True:
                level, operations, block = self._queue.popleft()
                await self._process_level_operations(level, operations, block)

    async def _synchronize(self, last_level: int, cache: bool = False) -> None:
        """Fetch operations via Fetcher and pass to message callback"""
        first_level = await self._enter_sync_state(last_level)
        if first_level is None:
            return

        self._logger.info('Fetching operations from level %s to %s', first_level, last_level)
        transaction_addresses = await self._get_transaction_addresses()
        origination_addresses = await self._get_origination_addresses()

        migration_originations = []
        if self._config.types and OperationType.migration in self._config.types:
            migration_originations = await self._datasource.get_migration_originations(first_level)
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
            await self._process_level_operations(level, operations)

        await self._exit_sync_state(last_level)

    async def _process_level_operations(self, level: int, operations: List[OperationData], block: Optional[HeadBlockData] = None) -> None:
        state = await self.get_state()
        if level < state.level:
            raise RuntimeError(f'Level of operation batch is lower than index state level: {level} < {state.level}')

        if self._rollback_level:
            if state.level != self._rollback_level:
                raise RuntimeError(f'Rolling back to level {self._rollback_level}, state level {state.level}')
            if level != self._rollback_level:
                raise RuntimeError(f'Rolling back to level {self._rollback_level}, got operations of level {level}')

            self._logger.info('Rolling back to previous level, verifying processed operations')
            expected_hashes = set(self._last_hashes)
            received_hashes = set([op.hash for op in operations])
            reused_hashes = received_hashes & expected_hashes
            if reused_hashes != expected_hashes:
                self._logger.warning('Attempted a single level rollback but arrived block differs from processed one')
                await self._ctx.reindex()

            self._rollback_level = None
            self._last_hashes = set()
            new_hashes = received_hashes - expected_hashes
            if not new_hashes:
                return
            operations = [op for op in operations if op.hash in new_hashes]

        async with in_global_transaction():
            self._logger.info('Processing %s operations of level %s', len(operations), level)
            await self._process_operations(operations)

            state.level = level  # type: ignore
            if block:
                state.hash = block.hash  # type: ignore
            await state.save()

    async def _match_operation(self, pattern_config: OperationHandlerPatternConfigT, operation: OperationData) -> bool:
        """Match single operation with pattern"""
        # NOTE: Reversed conditions are intentional
        if isinstance(pattern_config, OperationHandlerTransactionPatternConfig):
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

    async def _process_operations(self, operations: List[OperationData]) -> None:
        """Try to match operations in cache with all patterns from indexes. Must be wrapped in transaction."""
        self._last_hashes = set()
        operation_subgroups: Dict[OperationSubgroup, List[OperationData]] = defaultdict(list)
        for operation in operations:
            key = OperationSubgroup(operation.hash, operation.counter)
            operation_subgroups[key].append(operation)
            self._last_hashes.add(operation.hash)

        for operation_subgroup, operations in operation_subgroups.items():
            self._logger.debug('Matching %s', key)

            for handler_config in self._config.handlers:
                operation_idx = 0
                pattern_idx = 0
                matched_operations: List[Optional[OperationData]] = []

                # TODO: Ensure complex cases work, for ex. required argument after optional one
                # TODO: Add None to matched_operations where applicable (pattern is optional and operation not found)
                while operation_idx < len(operations):
                    operation, pattern_config = operations[operation_idx], handler_config.pattern[pattern_idx]
                    operation_matched = await self._match_operation(pattern_config, operation)

                    if operation.type == 'origination' and isinstance(pattern_config, OperationHandlerOriginationPatternConfig):

                        if operation_matched is True and pattern_config.origination_processed(
                            cast(str, operation.originated_contract_address)
                        ):
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
                        await self._on_match(operation_subgroup, handler_config, matched_operations)

                        matched_operations = []
                        pattern_idx = 0

                if len(matched_operations) >= sum(map(lambda x: 0 if x.optional else 1, handler_config.pattern)):
                    self._logger.info('%s: `%s` handler matched!', operation_subgroup.hash, handler_config.callback)
                    await self._on_match(operation_subgroup, handler_config, matched_operations)

    async def _on_match(
        self,
        operation_subgroup: OperationSubgroup,
        handler_config: OperationHandlerConfig,
        matched_operations: List[Optional[OperationData]],
    ):
        """Prepare handler arguments, parse parameter and storage. Schedule callback in executor."""
        args: List[Optional[Union[Transaction, Origination, OperationData]]] = []
        for pattern_config, operation in zip(handler_config.pattern, matched_operations):
            if operation is None:
                args.append(None)

            elif isinstance(pattern_config, OperationHandlerTransactionPatternConfig):
                if not pattern_config.entrypoint:
                    args.append(operation)
                    continue

                parameter_type = pattern_config.parameter_type_cls
                try:
                    parameter = parameter_type.parse_obj(operation.parameter_json) if parameter_type else None
                except ValidationError as e:
                    error_context = dict(
                        hash=operation.hash,
                        counter=operation.counter,
                        nonce=operation.nonce,
                    )
                    raise InvalidDataError(operation.parameter_json, parameter_type, error_context) from e

                storage_type = pattern_config.storage_type_cls
                storage = operation.get_merged_storage(storage_type)

                transaction_context = Transaction(
                    data=operation,
                    parameter=parameter,
                    storage=storage,
                )
                args.append(transaction_context)

            elif isinstance(pattern_config, OperationHandlerOriginationPatternConfig):
                storage_type = pattern_config.storage_type_cls
                storage = operation.get_merged_storage(storage_type)

                origination_context = Origination(
                    data=operation,
                    storage=storage,
                )
                args.append(origination_context)

            else:
                raise NotImplementedError

        logger = FormattedLogger(
            name=handler_config.callback,
            fmt=operation_subgroup.hash + ': {}',
        )
        handler_context = HandlerContext(
            datasources=self._ctx.datasources,
            config=self._ctx.config,
            logger=logger,
            template_values=self._config.template_values,
            datasource=self.datasource,
            index_config=self._config,
        )

        await handler_config.callback_fn(handler_context, *args)

        if handler_context.updated:
            self._ctx.commit()

    async def _get_transaction_addresses(self) -> Set[str]:
        """Get addresses to fetch transactions from during initial synchronization"""
        if self._config.types and OperationType.transaction not in self._config.types:
            return set()
        return set(cast(ContractConfig, c).address for c in self._config.contracts or [])

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
        self._queue: Deque[Tuple[int, List[BigMapData]]] = deque()

    def push(self, level: int, big_maps: List[BigMapData]):
        self._queue.append((level, big_maps))

    async def _process_queue(self):
        if not self._queue:
            return
        self._logger.info('Processing websocket queue')
        with suppress(IndexError):
            while True:
                level, big_maps = self._queue.popleft()
                await self._process_level_big_maps(level, big_maps)

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

        async for level, big_maps in fetcher.fetch_big_maps_by_level():
            await self._process_level_big_maps(level, big_maps)

        await self._exit_sync_state(last_level)

    async def _process_level_big_maps(self, level: int, big_maps: List[BigMapData]):
        state = await self.get_state()
        if state.level >= level:
            raise RuntimeError(state.level, level)

        async with in_global_transaction():
            self._logger.info('Processing %s big map diffs of level %s', len(big_maps), level)
            await self._process_big_maps(big_maps)

            state.level = level  # type: ignore
            await state.save()

    async def _match_big_map(self, handler_config: BigMapHandlerConfig, big_map: BigMapData) -> bool:
        """Match single big map diff with pattern"""
        if handler_config.path != big_map.path:
            return False
        if handler_config.contract_config.address != big_map.contract_address:
            return False
        return True

    async def _on_match(
        self,
        handler_config: BigMapHandlerConfig,
        matched_big_map: BigMapData,
    ) -> None:
        """Prepare handler arguments, parse key and value. Schedule callback in executor."""

        if matched_big_map.action.has_key:
            key_type = handler_config.key_type_cls
            try:
                key = key_type.parse_obj(matched_big_map.key)
            except ValidationError as e:
                raise InvalidDataError(matched_big_map.key, key_type) from e
        else:
            key = None

        if matched_big_map.action.has_value:
            value_type = handler_config.value_type_cls
            try:
                value = value_type.parse_obj(matched_big_map.value)
            except ValidationError as e:
                raise InvalidDataError(matched_big_map.key, value_type) from e
        else:
            value = None

        big_map_context = BigMapDiff(  # type: ignore
            data=matched_big_map,
            action=matched_big_map.action,
            key=key,
            value=value,
        )
        logger = FormattedLogger(
            name=handler_config.callback,
            fmt=str(matched_big_map.operation_id) + ': {}',
        )

        handler_context = HandlerContext(
            datasources=self._ctx.datasources,
            config=self._ctx.config,
            logger=logger,
            template_values=self._config.template_values,
            datasource=self.datasource,
            index_config=self._config,
        )

        await handler_config.callback_fn(handler_context, big_map_context)

        if handler_context.updated:
            self._ctx.commit()

    async def _process_big_maps(self, big_maps: List[BigMapData]) -> None:
        """Try to match big map diffs in cache with all patterns from indexes."""

        for big_map in big_maps:
            for handler_config in self._config.handlers:
                big_map_matched = await self._match_big_map(handler_config, big_map)
                if big_map_matched:
                    self._logger.info('%s: `%s` handler matched!', big_map.operation_id, handler_config.callback)
                    await self._on_match(handler_config, big_map)

    async def _get_big_map_addresses(self) -> Set[str]:
        """Get addresses to fetch transactions from during initial synchronization"""
        addresses = set()
        for handler_config in self._config.handlers:
            addresses.add(cast(ContractConfig, handler_config.contract).address)
        return addresses

    async def _get_big_map_paths(self) -> Set[str]:
        """Get addresses to fetch transactions from during initial synchronization"""
        paths = set()
        for handler_config in self._config.handlers:
            paths.add(handler_config.path)
        return paths
