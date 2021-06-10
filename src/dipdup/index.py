from collections import deque, namedtuple
from contextlib import suppress
import logging
from typing import Any, Deque, Dict, List, Optional, Set, Tuple, Union, cast
from dipdup.config import (
    BigMapHandlerConfig,
    BigMapHandlerPatternConfig,
    BigMapIndexConfig,
    ContractConfig,
    DipDupConfig,
    IndexConfig,
    OperationHandlerConfig,
    OperationHandlerOriginationPatternConfig,
    OperationHandlerPatternConfigT,
    OperationHandlerTransactionPatternConfig,
    OperationIndexConfig,
    OperationType,
)
from dipdup.datasources import DatasourceT
from dipdup.datasources.tzkt.datasource import BigMapFetcher, OperationFetcher, TzktDatasource
from dipdup.models import BigMapAction, BigMapContext, BigMapData, OperationData, OriginationContext, State, TransactionContext
from tortoise.transactions import in_transaction

from dipdup.utils import reindex, restart
from pydantic.dataclasses import dataclass


OperationGroup = namedtuple('OperationGroup', ('hash', 'counter'))


@dataclass
class HandlerContext:
    """Common handler context."""

    # FIXME: Add ForwardRefs
    datasources: Any  # Dict[str, DatasourceT]
    config: DipDupConfig

    def __post_init_post_parse__(self) -> None:
        self._updated: bool = False

    def commit(self) -> None:
        """Spawn indexes after handler execution"""
        self._updated = True

    def reset(self) -> None:
        self._updated = False

    @property
    def updated(self) -> bool:
        return self._updated

    async def reindex(self) -> None:
        await reindex()

    async def restart(self) -> None:
        await restart()

    # TODO
    async def add_contract(self):
        ...

    # TODO
    async def add_index(self):
        ...


@dataclass
class OperationHandlerContext(HandlerContext):
    """Operation index handler context (first argument)"""

    operations: List[OperationData]
    template_values: Optional[Dict[str, str]]


@dataclass
class BigMapHandlerContext(HandlerContext):
    """Big map index handler context (first argument)"""

    template_values: Optional[Dict[str, str]]


class Index:
    ...


class OperationIndex(Index):
    def __init__(self, ctx: HandlerContext, config: OperationIndexConfig, datasource: TzktDatasource) -> None:
        self._ctx = ctx
        self._config = config
        self._datasource = datasource

        self._logger = logging.getLogger(__name__)
        self._queue: Deque[Tuple[int, List[OperationData]]] = deque()

    @property
    def state(self) -> State:
        return self._config.state

    def push(self, level: int, operations: List[OperationData]):
        self._queue.append((level, operations))

    async def process(self) -> None:
        self._logger.info('Processing index `%s`', self._config.name)
        if self._datasource.sync_level is None:
            self._logger.info('Datasource is not active, sync to latest block')
            last_level = (await self._datasource.get_latest_block())['level']
            await self._synchronize(last_level)
        elif self._datasource.sync_level > self.state.level:
            self._logger.info('Index is behind datasource, sync to datasource level')
            last_level = self._datasource.sync_level
            await self._synchronize(last_level)
        else:
            self._logger.info('Processing websocket queue')
            await self._process_queue()

    async def _process_queue(self):
        with suppress(IndexError):
            while True:
                level, operations = self._queue.popleft()
                await self._process_level_operations(level, operations)

    async def _synchronize(self, last_level: int) -> None:
        """Fetch operations via Fetcher and pass to message callback"""
        first_level = self.state.level
        if first_level >= last_level:
            raise RuntimeError(first_level, last_level)

        self._logger.info('Fetching operations from level %s to %s', first_level, last_level)

        transaction_addresses = await self._get_transaction_addresses()
        origination_addresses = await self._get_origination_addresses()

        fetcher = OperationFetcher(
            datasource=self._datasource,
            first_level=first_level,
            last_level=last_level,
            transaction_addresses=transaction_addresses,
            origination_addresses=origination_addresses,
        )

        async for level, operations in fetcher.fetch_operations_by_level():
            self._logger.info('Processing %s operations of level %s', len(operations), level)
            await self._process_level_operations(level, operations)

        self.state.level = last_level  # type: ignore
        await self.state.save()

    async def _process_level_operations(self, level: int, operations: List[OperationData]):
        if self.state.level >= level:
            raise RuntimeError(self.state.level, level)

        async with in_transaction():
            await self._process_operations(operations)

            self.state.level = level  # type: ignore
            await self.state.save()

    def _match_operation(self, pattern_config: OperationHandlerPatternConfigT, operation: OperationData) -> bool:
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
                if pattern_config.strict:
                    if pattern_config.similar_to_contract_config.code_hash != operation.originated_contract_code_hash:
                        return False
                else:
                    if pattern_config.similar_to_contract_config.type_hash != operation.originated_contract_type_hash:
                        return False
            return True
        else:
            raise NotImplementedError

    async def _process_operations(self, operations: List[OperationData]) -> None:
        """Try to match operations in cache with all patterns from indexes."""
        operation_groups: Dict[OperationGroup, List[OperationData]] = {}
        for operation in operations:
            key = OperationGroup(operation.hash, operation.counter)
            if key not in operation_groups:
                operation_groups[key] = []
            operation_groups[key].append(operation)

        keys = list(operation_groups.keys())
        self._logger.info('Matching %s operation groups', len(keys))
        for key, operations in operation_groups.items():
            self._logger.debug('Matching %s', key)

            for handler_config in self._config.handlers:
                operation_idx = 0
                pattern_idx = 0
                matched_operations: List[Optional[OperationData]] = []

                # TODO: Ensure complex cases work, for ex. required argument after optional one
                # TODO: Add None to matched_operations where applicable (pattern is optional and operation not found)
                while operation_idx < len(operations):
                    operation, pattern_config = operations[operation_idx], handler_config.pattern[pattern_idx]
                    operation_matched = self._match_operation(pattern_config, operation)

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
                        self._logger.info('Handler `%s` matched! %s', handler_config.callback, key)
                        await self._on_match(handler_config, matched_operations, operations)

                        matched_operations = []
                        pattern_idx = 0

                if len(matched_operations) >= sum(map(lambda x: 0 if x.optional else 1, handler_config.pattern)):
                    self._logger.info('Handler `%s` matched! %s', handler_config.callback, key)
                    await self._on_match(handler_config, matched_operations, operations)

    async def _on_match(
        self,
        handler_config: OperationHandlerConfig,
        matched_operations: List[Optional[OperationData]],
        operations: List[OperationData],
    ):
        """Prepare handler arguments, parse parameter and storage. Schedule callback in executor."""
        args: List[Optional[Union[TransactionContext, OriginationContext, OperationData]]] = []
        for pattern_config, operation in zip(handler_config.pattern, matched_operations):
            if operation is None:
                args.append(None)

            elif isinstance(pattern_config, OperationHandlerTransactionPatternConfig):
                if not pattern_config.entrypoint:
                    args.append(operation)
                    continue

                parameter_type = pattern_config.parameter_type_cls
                parameter = parameter_type.parse_obj(operation.parameter_json) if parameter_type else None

                storage_type = pattern_config.storage_type_cls
                storage = operation.get_merged_storage(storage_type)

                transaction_context = TransactionContext(
                    data=operation,
                    parameter=parameter,
                    storage=storage,
                )
                args.append(transaction_context)

            elif isinstance(pattern_config, OperationHandlerOriginationPatternConfig):
                storage_type = pattern_config.storage_type_cls
                storage = operation.get_merged_storage(storage_type)

                origination_context = OriginationContext(
                    data=operation,
                    storage=storage,
                )
                args.append(origination_context)

            else:
                raise NotImplementedError

        handler_context = OperationHandlerContext(
            datasources=self._ctx.datasources,
            config=self._ctx.config,
            operations=operations,
            template_values=self._config.template_values,
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
        return set(addresses)


class BigMapIndex:
    def __init__(self, ctx: HandlerContext, config: BigMapIndexConfig, datasource: TzktDatasource) -> None:
        self._ctx = ctx
        self._config = config
        self._datasource = datasource

        self._logger = logging.getLogger(__name__)
        self._queue: Deque[Tuple[int, List[BigMapData]]] = deque()

    @property
    def state(self) -> State:
        return self._config.state

    def push(self, level: int, big_maps: List[BigMapData]):
        self._queue.append((level, big_maps))

    async def process(self) -> None:
        self._logger.info('Processing index `%s`', self._config.name)
        if self._datasource.sync_level is None:
            self._logger.info('Datasource is not active, sync to latest block')
            last_level = (await self._datasource.get_latest_block())['level']
            await self._synchronize(last_level)
        elif self._datasource.sync_level > self.state.level:
            self._logger.info('Index is behind datasource, sync to datasource level')
            last_level = self._datasource.sync_level
            await self._synchronize(last_level)
        else:
            self._logger.info('Processing websocket queue')
            await self._process_queue()

    async def _process_queue(self):
        with suppress(IndexError):
            while True:
                level, big_maps = self._queue.popleft()
                await self._process_level_big_maps(level, big_maps)

    async def _synchronize(self, last_level: int) -> None:
        """Fetch operations via Fetcher and pass to message callback"""
        first_level = self.state.level
        if first_level >= last_level:
            raise RuntimeError(first_level, last_level)

        self._logger.info('Fetching operations from level %s to %s', first_level, last_level)

        big_map_addresses = await self._get_big_map_addresses()
        big_map_paths = await self._get_big_map_paths()

        fetcher = BigMapFetcher(
            datasource=self._datasource,
            first_level=first_level,
            last_level=last_level,
            big_map_addresses=big_map_addresses,
            big_map_paths=big_map_paths,
        )

        async for level, big_maps in fetcher.fetch_big_maps_by_level():
            self._logger.info('Processing %s big map diffs of level %s', len(big_maps), level)
            await self._process_level_big_maps(level, big_maps)

        self.state.level = last_level  # type: ignore
        await self.state.save()

    async def _process_level_big_maps(self, level: int, big_maps: List[BigMapData]):
        if self.state.level >= level:
            raise RuntimeError(self.state.level, level)

        async with in_transaction():
            await self._process_big_maps(big_maps)

            self.state.level = level  # type: ignore
            await self.state.save()

    def _match_big_map(self, pattern_config: BigMapHandlerPatternConfig, big_map: BigMapData) -> bool:
        """Match single big map diff with pattern"""
        if pattern_config.path != big_map.path:
            return False
        if pattern_config.contract_config.address != big_map.contract_address:
            return False
        return True

    async def _on_match(
        self,
        handler_config: BigMapHandlerConfig,
        matched_big_maps: List[List[BigMapData]],
    ) -> None:
        """Prepare handler arguments, parse key and value. Schedule callback in executor."""
        args: List[List[BigMapContext]] = []
        for matched_big_map_group, pattern_config in zip(matched_big_maps, handler_config.pattern):
            big_map_contexts = []
            for big_map in matched_big_map_group:
                if big_map.action == BigMapAction.ALLOCATE:
                    continue

                key_type = pattern_config.key_type_cls
                key = key_type.parse_obj(big_map.key)

                if big_map.action == BigMapAction.REMOVE:
                    value = None
                else:
                    value_type = pattern_config.value_type_cls
                    value = value_type.parse_obj(big_map.value)

                big_map_context = BigMapContext(  # type: ignore
                    action=big_map.action,
                    key=key,
                    value=value,
                )

                big_map_contexts.append(big_map_context)

            args.append(big_map_contexts)

        handler_context = BigMapHandlerContext(
            datasources=self._ctx.datasources,
            config=self._ctx.config,
            template_values=self._config.template_values,
        )

        await handler_config.callback_fn(handler_context, *args)

        if handler_context.updated:
            self._ctx.commit()

    async def _process_big_maps(self, big_maps: List[BigMapData]) -> None:
        """Try to match big map diffs in cache with all patterns from indexes."""

        # FIXME: groupby
        big_map_groups: Dict[int, List[BigMapData]] = {}
        for big_map in big_maps:
            key = big_map.operation_id
            if key not in big_map_groups:
                big_map_groups[key] = []
            big_map_groups[key].append(big_map)

        keys = list(big_map_groups.keys())
        self._logger.info('Matching %s big map groups', len(keys))
        for key, big_maps in big_map_groups.items():
            self._logger.debug('Processing %s', key)

            for handler_config in self._config.handlers:
                matched_big_maps: List[List[BigMapData]] = [[] for _ in range(len(handler_config.pattern))]
                for i, pattern_config in enumerate(handler_config.pattern):
                    for big_map in big_maps:
                        big_map_matched = self._match_big_map(pattern_config, big_map)
                        if big_map_matched:
                            matched_big_maps[i].append(big_map)

                if any([len(big_map_group) for big_map_group in matched_big_maps]):
                    self._logger.info('Handler `%s` matched! %s', handler_config.callback, key)
                    await self._on_match(handler_config, matched_big_maps)
                    break

    async def _get_big_map_addresses(self) -> Set[str]:
        """Get addresses to fetch transactions from during initial synchronization"""
        addresses = set()
        for handler_config in self._config.handlers:
            for pattern_config in handler_config.pattern:
                addresses.add(cast(ContractConfig, pattern_config.contract).address)
        return addresses

    async def _get_big_map_paths(self) -> Set[str]:
        """Get addresses to fetch transactions from during initial synchronization"""
        paths = set()
        for handler_config in self._config.handlers:
            for pattern_config in handler_config.pattern:
                paths.add(pattern_config.path)
        return paths
