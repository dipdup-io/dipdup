import logging
from collections import namedtuple
from copy import copy
from typing import Awaitable, Callable, Dict, List, Optional

from dipdup.config import (
    BigMapHandlerConfig,
    BigMapHandlerPatternConfig,
    BigMapIndexConfig,
    OperationHandlerConfig,
    OperationHandlerOriginationPatternConfig,
    OperationHandlerPatternConfigT,
    OperationHandlerTransactionPatternConfig,
    OperationIndexConfig,
)
from dipdup.models import BigMapData, OperationData

OperationGroup = namedtuple('OperationGroup', ('hash', 'counter'))
OperationID = int


class OperationCache:
    def __init__(self) -> None:
        super().__init__()
        self._logger = logging.getLogger(__name__)
        self._level: Optional[int] = None
        self._indexes: Dict[str, OperationIndexConfig] = {}
        self._operations: Dict[OperationGroup, List[OperationData]] = {}

    async def add_index(self, index_config: OperationIndexConfig) -> None:
        self._logger.debug('Adding index %s to cache', index_config)
        for contract in index_config.contract_configs:
            if contract.address in self._indexes:
                raise RuntimeError(f'Address `{contract.address}` used in multiple indexes')
            self._indexes[contract.address] = index_config

    async def add(self, operation: OperationData):
        self._logger.debug('Adding operation %s to cache (%s, %s)', operation.id, operation.hash, operation.counter)
        self._logger.debug('level=%s operation.level=%s', self._level, operation.level)

        if self._level is not None:
            if self._level != operation.level:
                raise RuntimeError('Operations must be splitted by level before caching')
        else:
            self._level = operation.level

        key = OperationGroup(operation.hash, operation.counter)
        if key not in self._operations:
            self._operations[key] = []
        self._operations[key].append(operation)

    def match_operation(self, pattern_config: OperationHandlerPatternConfigT, operation: OperationData) -> bool:
        if isinstance(pattern_config, OperationHandlerTransactionPatternConfig):
            if pattern_config.entrypoint != operation.entrypoint:
                return False
            if pattern_config.destination and pattern_config.destination_contract_config.address != operation.target_address:
                return False
            if pattern_config.source and pattern_config.source_contract_config.address != operation.sender_address:
                return False
            return True
        if isinstance(pattern_config, OperationHandlerOriginationPatternConfig):
            return pattern_config.contract_config.address == operation.originated_contract_address
        raise NotImplementedError

    async def process(
        self,
        callback: Callable[
            [OperationIndexConfig, OperationHandlerConfig, List[Optional[OperationData]], List[OperationData]],
            Awaitable[None],
        ],
    ) -> int:
        async def on_match(
            key: OperationGroup,
            index_config: OperationIndexConfig,
            handler_config: OperationHandlerConfig,
            matched_operations: List[Optional[OperationData]],
            operations: List[OperationData],
        ) -> None:
            self._logger.info('Handler `%s` matched! %s', handler_config.callback, key)
            await callback(index_config, handler_config, matched_operations, operations)

            index_config.state.level = self._level
            await index_config.state.save()

        if self._level is None:
            raise RuntimeError('Add operations to cache before processing')

        keys = list(self._operations.keys())
        self._logger.info('Matching %s operation groups', len(keys))
        for key, operations in self._operations.items():
            self._logger.debug('Matching %s', key)
            matched = False

            for index_config in self._indexes.values():
                for handler_config in index_config.handlers:
                    operation_idx = 0
                    pattern_idx = 0
                    matched_operations: List[Optional[OperationData]] = []

                    while operation_idx < len(operations):
                        pattern_config = handler_config.pattern[pattern_idx]
                        matched = self.match_operation(pattern_config, operations[operation_idx])
                        if matched:
                            matched_operations.append(operations[operation_idx])
                            pattern_idx += 1
                            operation_idx += 1
                        elif pattern_config.optional:
                            matched_operations.append(None)
                            pattern_idx += 1
                        else:
                            operation_idx += 1

                        if pattern_idx == len(handler_config.pattern):
                            await on_match(key, index_config, handler_config, matched_operations, operations)
                            matched = True
                            matched_operations = []
                            pattern_idx = 0

                    if len(matched_operations) >= sum(map(lambda x: 0 if x.optional else 1, handler_config.pattern)):
                        await on_match(key, index_config, handler_config, matched_operations, operations)
                        matched = True

                # NOTE: Only one index could match as addresses do not intersect between indexes (checked on config initialization)
                if matched:
                    break

        self._logger.info('Current level: %s', self._level)
        self._operations = {}

        level = self._level
        self._level = None
        return level

    @property
    def level(self) -> Optional[int]:
        return self._level


class BigMapCache:
    def __init__(self) -> None:
        super().__init__()
        self._logger = logging.getLogger(__name__)
        self._level: Optional[int] = None
        self._indexes: List[BigMapIndexConfig] = []
        self._big_maps: Dict[OperationID, List[BigMapData]] = {}

    async def add_index(self, index_config: BigMapIndexConfig) -> None:
        self._logger.debug('Adding index %s to cache', index_config)
        self._indexes.append(index_config)

    async def add(self, big_map: BigMapData):
        self._logger.debug('Adding big map %s to cache (%s)', big_map.id, big_map.operation_id)
        self._logger.debug('level=%s operation.level=%s', self._level, big_map.level)

        if self._level is not None:
            if self._level != big_map.level:
                raise RuntimeError('Big maps must be splitted by level before caching')
        else:
            self._level = big_map.level

        key = big_map.operation_id
        if key not in self._big_maps:
            self._big_maps[key] = []
        self._big_maps[key].append(big_map)

    def match_big_map(self, pattern_config: BigMapHandlerPatternConfig, big_map: BigMapData) -> bool:
        self._logger.debug('pattern: %s, %s', pattern_config.path, pattern_config.contract_config.address)
        self._logger.debug('big_map: %s, %s', big_map.path, big_map.contract_address)
        if pattern_config.path != big_map.path:
            return False
        if pattern_config.contract_config.address != big_map.contract_address:
            return False
        self._logger.debug('match!')
        return True

    async def process(
        self,
        callback: Callable[[BigMapIndexConfig, BigMapHandlerConfig, List[List[BigMapData]]], Awaitable[None]],
    ) -> int:
        if self._level is None:
            raise RuntimeError('Add big maps to cache before processing')

        keys = list(self._big_maps.keys())
        self._logger.info('Matching %s big map groups', len(keys))
        for key, big_maps in copy(self._big_maps).items():
            self._logger.debug('Processing %s', key)
            matched = False

            for index_config in self._indexes:
                if matched:
                    break
                for handler_config in index_config.handlers:
                    matched_big_maps: List[List[BigMapData]] = [[] for _ in range(len(handler_config.pattern))]
                    for i, pattern_config in enumerate(handler_config.pattern):
                        for big_map in big_maps:
                            big_map_matched = self.match_big_map(pattern_config, big_map)
                            if big_map_matched:
                                matched_big_maps[i].append(big_map)

                    if any([len(big_map_group) for big_map_group in matched_big_maps]):
                        self._logger.info('Handler `%s` matched! %s', handler_config.callback, key)
                        matched = True
                        await callback(index_config, handler_config, matched_big_maps)

                        index_config.state.level = self._level
                        await index_config.state.save()

                        del self._big_maps[key]
                        break

        keys_left = self._big_maps.keys()
        self._logger.info('%s operation groups unmatched', len(keys_left))
        self._logger.info('Current level: %s', self._level)
        self._big_maps = {}

        level = self._level
        self._level = None
        return level

    @property
    def level(self) -> Optional[int]:
        return self._level
