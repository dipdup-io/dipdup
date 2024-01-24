import logging
from collections import deque
from collections.abc import Iterable
from typing import Any

from pydantic.dataclasses import dataclass

from dipdup.codegen.tezos_tzkt import get_parameter_type
from dipdup.codegen.tezos_tzkt import get_storage_type
from dipdup.config.tezos_tzkt_operations import OperationsHandlerOriginationPatternConfig as OriginationPatternConfig
from dipdup.config.tezos_tzkt_operations import (
    OperationsHandlerSmartRollupExecutePatternConfig as SmartRollupExecutePatternConfig,
)
from dipdup.config.tezos_tzkt_operations import OperationsHandlerTransactionPatternConfig as TransactionPatternConfig
from dipdup.config.tezos_tzkt_operations import TzktOperationsHandlerConfig
from dipdup.config.tezos_tzkt_operations import TzktOperationsHandlerConfigU
from dipdup.config.tezos_tzkt_operations import TzktOperationsUnfilteredIndexConfig
from dipdup.exceptions import FrameworkException
from dipdup.indexes.tezos_tzkt_operations.parser import deserialize_storage
from dipdup.models.tezos_tzkt import TzktOperationData
from dipdup.models.tezos_tzkt import TzktOperationType
from dipdup.models.tezos_tzkt import TzktOrigination
from dipdup.models.tezos_tzkt import TzktSmartRollupExecute
from dipdup.models.tezos_tzkt import TzktTransaction
from dipdup.package import DipDupPackage
from dipdup.utils import parse_object

_logger = logging.getLogger('dipdup.matcher')


@dataclass(frozen=True)
class OperationSubgroup:
    """Operations of a single contract call"""

    hash: str
    counter: int
    operations: tuple[TzktOperationData, ...]
    entrypoints: set[str | None]


OperationsHandlerArgumentU = (
    TzktTransaction[Any, Any] | TzktOrigination[Any] | TzktSmartRollupExecute | TzktOperationData | None
)
MatchedOperationsT = tuple[OperationSubgroup, TzktOperationsHandlerConfigU, deque[OperationsHandlerArgumentU]]


def prepare_operation_handler_args(
    package: DipDupPackage,
    handler_config: TzktOperationsHandlerConfig,
    matched_operations: deque[TzktOperationData | None],
) -> deque[OperationsHandlerArgumentU]:
    """Prepare handler arguments, parse parameter and storage."""
    args: deque[OperationsHandlerArgumentU] = deque()
    for pattern_config, operation_data in zip(handler_config.pattern, matched_operations, strict=True):
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

            typed_transaction: TzktTransaction[Any, Any] = TzktTransaction(
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

            typed_origination = TzktOrigination(
                data=operation_data,
                storage=storage,
            )
            args.append(typed_origination)

        elif isinstance(pattern_config, SmartRollupExecutePatternConfig):
            sr_execute: TzktSmartRollupExecute = TzktSmartRollupExecute.create(operation_data)
            args.append(sr_execute)

        else:
            raise NotImplementedError

    return args


def match_transaction(
    pattern_config: TransactionPatternConfig,
    operation: TzktOperationData,
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
    operation: TzktOperationData,
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
    operation: TzktOperationData,
) -> bool:
    if source := pattern_config.source:
        if source.address not in (operation.sender_address, None):
            return False
    if destination := pattern_config.destination:
        if destination.address not in (operation.target_address, None):
            return False

    return True


def match_operation_unfiltered_subgroup(
    index: TzktOperationsUnfilteredIndexConfig,
    operation_subgroup: OperationSubgroup,
) -> deque[MatchedOperationsT]:
    matched_handlers: deque[MatchedOperationsT] = deque()

    for operation in operation_subgroup.operations:
        if TzktOperationType[operation.type] in index.types:
            matched_handlers.append((operation_subgroup, index.handler_config, deque([operation])))

    return matched_handlers


def match_operation_subgroup(
    package: DipDupPackage,
    handlers: Iterable[TzktOperationsHandlerConfig],
    operation_subgroup: OperationSubgroup,
    alt: bool = False,
) -> deque[MatchedOperationsT]:
    """Try to match operation subgroup with all index handlers."""
    matched_handlers: deque[MatchedOperationsT] = deque()
    operations = operation_subgroup.operations

    for handler_config in handlers:
        subgroup_index = 0
        pattern_index = 0
        matched_operations: deque[TzktOperationData | None] = deque()

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
                matched_handlers.append((operation_subgroup, handler_config, args))

                matched_operations.clear()
                pattern_index = 0

        if len(matched_operations) >= sum(0 if x.optional else 1 for x in handler_config.pattern):
            _logger.debug('%s: `%s` handler matched!', operation_subgroup.hash, handler_config.callback)

            args = prepare_operation_handler_args(package, handler_config, matched_operations)
            matched_handlers.append((operation_subgroup, handler_config, args))

    if not (alt and len(matched_handlers) in (0, 1)):
        return matched_handlers

    # NOTE: Alternative algorithm. Sort matched handlers by the internal incremental TzKT id of the last operation in matched pattern.
    index_list = list(range(len(matched_handlers)))
    id_list = []
    for handler in matched_handlers:
        last_operation = handler[2][-1]
        if isinstance(last_operation, TzktOperationData):
            id_list.append(last_operation.id)
        elif isinstance(last_operation, TzktOrigination):
            id_list.append(last_operation.data.id)
        elif isinstance(last_operation, TzktTransaction):
            id_list.append(last_operation.data.id)
        elif isinstance(last_operation, TzktSmartRollupExecute):
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
