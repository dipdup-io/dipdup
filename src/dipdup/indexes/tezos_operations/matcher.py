from __future__ import annotations

import logging
from collections import deque
from typing import TYPE_CHECKING
from typing import Any

from pydantic.dataclasses import dataclass

from dipdup.codegen.tezos import get_parameter_type
from dipdup.codegen.tezos import get_storage_type
from dipdup.config.tezos_operations import TezosOperationsHandlerConfig
from dipdup.config.tezos_operations import TezosOperationsHandlerConfigU
from dipdup.config.tezos_operations import TezosOperationsHandlerOriginationPatternConfig as OriginationPatternConfig
from dipdup.config.tezos_operations import (
    TezosOperationsHandlerSmartRollupCementPatternConfig as SmartRollupCementPatternConfig,
)
from dipdup.config.tezos_operations import (
    TezosOperationsHandlerSmartRollupExecutePatternConfig as SmartRollupExecutePatternConfig,
)
from dipdup.config.tezos_operations import TezosOperationsHandlerTransactionPatternConfig as TransactionPatternConfig
from dipdup.config.tezos_operations import TezosOperationsUnfilteredIndexConfig
from dipdup.exceptions import FrameworkException
from dipdup.indexes.tezos_operations.parser import deserialize_storage
from dipdup.models.tezos import TezosOperationData
from dipdup.models.tezos import TezosOperationType
from dipdup.models.tezos import TezosOrigination
from dipdup.models.tezos import TezosSmartRollupCement
from dipdup.models.tezos import TezosSmartRollupExecute
from dipdup.models.tezos import TezosTransaction
from dipdup.package import DipDupPackage
from dipdup.utils import parse_object

if TYPE_CHECKING:
    from collections.abc import Iterable

_logger = logging.getLogger('dipdup.matcher')


@dataclass(frozen=True)
class OperationSubgroup:
    """Operations of a single contract call"""

    hash: str
    counter: int
    operations: tuple[TezosOperationData, ...]

    @property
    def level(self) -> int:
        return self.operations[0].level

    def __len__(self) -> int:
        return len(self.operations)


TezosOperationsHandlerArgumentU = (
    TezosTransaction[Any, Any]
    | TezosOrigination[Any]
    | TezosSmartRollupExecute
    | TezosSmartRollupCement
    | TezosOperationData
    | None
)
MatchedOperationsT = tuple[TezosOperationsHandlerConfigU, deque[TezosOperationsHandlerArgumentU]]


def prepare_operation_handler_args(
    package: DipDupPackage,
    handler_config: TezosOperationsHandlerConfig,
    matched_operations: deque[TezosOperationData | None],
) -> deque[TezosOperationsHandlerArgumentU]:
    """Prepare handler arguments, parse parameter and storage."""
    args: deque[TezosOperationsHandlerArgumentU] = deque()
    # NOTE: There can be more pattern items than matched operations; some of them are optional.
    for pattern_config, operation_data in zip(handler_config.pattern, matched_operations, strict=False):
        if operation_data is None:
            args.append(None)

        elif isinstance(pattern_config, TransactionPatternConfig):
            if not pattern_config.typed_contract or not pattern_config.entrypoint:
                args.append(operation_data)
                continue

            typename = pattern_config.typed_contract.module_name
            type_ = get_parameter_type(package, typename, pattern_config.entrypoint)
            parameter = parse_object(type_, operation_data.parameter_json) if type_ else None

            storage_type = get_storage_type(package, typename)
            operation_data, storage = deserialize_storage(operation_data, storage_type)

            typed_transaction: TezosTransaction[Any, Any] = TezosTransaction(
                data=operation_data,
                parameter=parameter,
                storage=storage,
            )
            args.append(typed_transaction)

        elif isinstance(pattern_config, OriginationPatternConfig):
            if not pattern_config.typed_contract:
                args.append(operation_data)
                continue

            typename = pattern_config.typed_contract.module_name
            storage_type = get_storage_type(package, typename)
            operation_data, storage = deserialize_storage(operation_data, storage_type)

            typed_origination = TezosOrigination(
                data=operation_data,
                storage=storage,
            )
            args.append(typed_origination)

        elif isinstance(pattern_config, SmartRollupExecutePatternConfig):
            sr_execute: TezosSmartRollupExecute = TezosSmartRollupExecute.create(operation_data)
            args.append(sr_execute)

        elif isinstance(pattern_config, SmartRollupCementPatternConfig):
            sr_cement: TezosSmartRollupCement = TezosSmartRollupCement.create(operation_data)
            args.append(sr_cement)

        else:
            raise NotImplementedError

    return args


def match_transaction(
    pattern_config: TransactionPatternConfig,
    operation: TezosOperationData,
) -> bool:
    """Match a single transaction with pattern"""
    if entrypoint := pattern_config.entrypoint:
        if entrypoint != operation.entrypoint:
            return False
    if destination := pattern_config.destination:
        if destination.address not in (operation.target_address, None):
            return False
        if destination.resolved_code_hash not in (operation.target_code_hash, None):
            return False
    if source := pattern_config.source:
        if source.address not in (operation.sender_address, None):
            return False
        if source.resolved_code_hash not in (operation.sender_code_hash, None):
            return False

    return True


def match_origination(
    pattern_config: OriginationPatternConfig,
    operation: TezosOperationData,
) -> bool:
    if source := pattern_config.source:
        if source.address not in (operation.sender_address, None):
            return False
        if source.code_hash:
            raise FrameworkException('Invalid origination filter `source.code_hash`')

    if originated_contract := pattern_config.originated_contract:
        if originated_contract.address not in (operation.originated_contract_address, None):
            return False
        if originated_contract.code_hash not in (operation.originated_contract_code_hash, None):
            return False

    return True


def match_sr_execute(
    pattern_config: SmartRollupExecutePatternConfig,
    operation: TezosOperationData,
) -> bool:
    if source := pattern_config.source:
        if source.address not in (operation.sender_address, None):
            return False
    if destination := pattern_config.destination:
        if destination.address not in (operation.target_address, None):
            return False

    return True


def match_sr_cement(
    pattern_config: SmartRollupCementPatternConfig,
    operation: TezosOperationData,
) -> bool:
    if source := pattern_config.source:
        if source.address not in (operation.sender_address, None):
            return False
    if destination := pattern_config.destination:
        if destination.address not in (operation.target_address, None):
            return False

    return True


def match_operation_unfiltered_subgroup(
    index: TezosOperationsUnfilteredIndexConfig,
    operation_subgroup: OperationSubgroup,
) -> deque[MatchedOperationsT]:
    matched_handlers: deque[MatchedOperationsT] = deque()

    for operation in operation_subgroup.operations:
        if TezosOperationType[operation.type] in index.types:
            matched_handlers.append((index.handlers[0], deque([operation])))

    return matched_handlers


def match_operation_subgroup(
    package: DipDupPackage,
    handlers: Iterable[TezosOperationsHandlerConfig],
    operation_subgroup: OperationSubgroup,
    alt: bool = False,
) -> deque[MatchedOperationsT]:
    """Try to match operation subgroup with all index handlers."""
    matched_handlers: deque[MatchedOperationsT] = deque()
    operations = operation_subgroup.operations

    for handler_config in handlers:
        subgroup_index = 0
        pattern_index = 0
        matched_operations: deque[TezosOperationData | None] = deque()

        # TODO: Ensure complex cases work, e.g. when optional argument is followed by required one
        while subgroup_index < len(operations):
            operation = operations[subgroup_index]
            pattern_config = handler_config.pattern[pattern_index]

            matched = False
            if isinstance(pattern_config, TransactionPatternConfig):
                if operation.type == 'transaction':
                    matched = match_transaction(pattern_config, operation)
            elif isinstance(pattern_config, OriginationPatternConfig):
                if operation.type == 'origination':
                    matched = match_origination(pattern_config, operation)
            elif isinstance(pattern_config, SmartRollupExecutePatternConfig):
                if operation.type == 'sr_execute':
                    matched = match_sr_execute(pattern_config, operation)
            elif isinstance(pattern_config, SmartRollupCementPatternConfig):
                if operation.type == 'sr_cement':
                    matched = match_sr_cement(pattern_config, operation)
            else:
                raise FrameworkException('Unsupported pattern type')

            if matched:
                matched_operations.append(operation)
                pattern_index += 1
                subgroup_index += 1
            elif pattern_config.optional:
                matched_operations.append(None)
                pattern_index += 1
            else:
                subgroup_index += 1

            if pattern_index == len(handler_config.pattern):
                _logger.debug('%s: `%s` handler matched!', operation_subgroup.hash, handler_config.callback)

                args = prepare_operation_handler_args(package, handler_config, matched_operations)
                matched_handlers.append((handler_config, args))

                matched_operations.clear()
                pattern_index = 0

        if len(matched_operations) >= sum(0 if x.optional else 1 for x in handler_config.pattern):
            _logger.debug('%s: `%s` handler matched!', operation_subgroup.hash, handler_config.callback)

            args = prepare_operation_handler_args(package, handler_config, matched_operations)
            matched_handlers.append((handler_config, args))

    if not (alt and len(matched_handlers) in (0, 1)):
        return matched_handlers

    # NOTE: Alternative algorithm. Sort matched handlers by the internal incremental TzKT id of the last operation in matched pattern.
    index_list = list(range(len(matched_handlers)))
    id_list = []
    for handler in matched_handlers:
        last_operation = handler[1][-1]
        if isinstance(last_operation, TezosOperationData):
            id_list.append(last_operation.id)
        elif isinstance(last_operation, TezosOrigination):
            id_list.append(last_operation.data.id)
        elif isinstance(last_operation, TezosTransaction):
            id_list.append(last_operation.data.id)
        elif isinstance(last_operation, TezosSmartRollupExecute):
            id_list.append(last_operation.data.id)
        else:
            raise FrameworkException('Type of the first handler argument is unknown')

    sorted_index_list = [x for _, x in sorted(zip(id_list, index_list, strict=True))]
    if index_list == sorted_index_list:
        return matched_handlers

    sorted_matched_handlers: deque[MatchedOperationsT] = deque()
    for index in sorted_index_list:
        sorted_matched_handlers.append(matched_handlers[index])
    return sorted_matched_handlers
