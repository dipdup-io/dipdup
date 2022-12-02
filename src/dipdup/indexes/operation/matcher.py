import logging
from collections import deque
from typing import Any
from typing import Iterable
from typing import TypeVar
from typing import cast

from pydantic.dataclasses import dataclass

from dipdup.config import OperationHandlerConfig
from dipdup.config import OperationHandlerOriginationPatternConfig as OriginationPatternConfig
from dipdup.config import OperationHandlerTransactionPatternConfig as TransactionPatternConfig
from dipdup.config import ResolvedIndexConfigU
from dipdup.datasources.tzkt.models import deserialize_storage
from dipdup.exceptions import FrameworkException
from dipdup.models import OperationData
from dipdup.models import Origination
from dipdup.models import Transaction
from dipdup.utils.codegen import parse_object

_logger = logging.getLogger('dipdup.matcher')

ConfigT = TypeVar('ConfigT', bound=ResolvedIndexConfigU)


@dataclass(frozen=True)
class OperationSubgroup:
    """Operations of a single contract call"""

    hash: str
    counter: int
    operations: tuple[OperationData, ...]
    entrypoints: set[str | None]


OperationHandlerArgumentT = Transaction | Origination | OperationData | None

MatchedOperationsT = tuple[OperationSubgroup, OperationHandlerConfig, deque[OperationHandlerArgumentT]]


def prepare_operation_handler_args(
    handler_config: OperationHandlerConfig,
    matched_operations: deque[OperationData | None],
) -> deque[OperationHandlerArgumentT]:
    """Prepare handler arguments, parse parameter and storage."""
    args: deque[OperationHandlerArgumentT] = deque()
    for pattern_config, operation_data in zip(handler_config.pattern, matched_operations):
        if operation_data is None:
            args.append(None)

        elif isinstance(pattern_config, TransactionPatternConfig):
            if not pattern_config.entrypoint:
                args.append(operation_data)
                continue

            type_ = pattern_config.parameter_type_cls
            parameter = parse_object(type_, operation_data.parameter_json) if type_ else None

            storage_type = pattern_config.storage_type_cls
            storage = deserialize_storage(operation_data, storage_type)

            typed_transaction: Transaction[Any, Any] = Transaction(
                data=operation_data,
                parameter=parameter,
                storage=storage,
            )
            args.append(typed_transaction)

        elif isinstance(pattern_config, OriginationPatternConfig):
            if pattern_config.originated_contract:
                pass
            elif pattern_config.similar_to and pattern_config.similar_to.address:
                pass
            else:
                args.append(operation_data)
                continue

            storage_type = pattern_config.storage_type_cls
            storage = deserialize_storage(operation_data, storage_type)

            typed_origination = Origination(
                data=operation_data,
                storage=storage,
            )
            args.append(typed_origination)

        else:
            raise NotImplementedError

    return args


def match_transaction(
    pattern_config: TransactionPatternConfig,
    operation: OperationData,
) -> bool:
    """Match a single transaction with pattern"""
    logging.info('match_transaction', pattern_config, operation)
    if pattern_config.entrypoint:
        if pattern_config.entrypoint != operation.entrypoint:
            return False
    if pattern_config.destination:
        if pattern_config.destination.address != operation.target_address:
            return False
    if pattern_config.source:
        if pattern_config.source.address != operation.sender_address:
            return False

    # TODO: Match by code hash

    return True


def match_origination(
    pattern_config: OriginationPatternConfig,
    operation: OperationData,
) -> bool:
    if source := pattern_config.source:
        if source.address not in (operation.sender_address, None):
            return False
    if contract := pattern_config.originated_contract:
        if contract.address not in (operation.originated_contract_address, None):
            return False
    if similar_to := pattern_config.similar_to:
        if similar_to.address not in (operation.originated_contract_address, None):
            return False

    # TODO: Match by code hash

    return True


def match_operation_subgroup(
    handlers: Iterable[OperationHandlerConfig],
    operation_subgroup: OperationSubgroup,
) -> deque[MatchedOperationsT]:
    """Try to match operation subgroup with all index handlers."""
    matched_handlers: deque[MatchedOperationsT] = deque()
    operations = operation_subgroup.operations

    for handler_config in handlers:
        subgroup_index = 0
        pattern_index = 0
        matched_operations: deque[OperationData | None] = deque()

        # TODO: Ensure complex cases work, e.g. when optional argument is followed by required one
        # TODO: Add None to matched_operations where applicable (pattern is optional and operation not found)
        while subgroup_index < len(operations):
            operation = operations[subgroup_index]
            pattern_config = handler_config.pattern[pattern_index]

            if isinstance(pattern_config, TransactionPatternConfig):
                matched = match_transaction(pattern_config, operation)
            elif isinstance(pattern_config, OriginationPatternConfig):
                matched = match_origination(pattern_config, operation)

                # TODO: Explain what's going on here
                if matched and pattern_config.origination_processed(cast(str, operation.originated_contract_code_hash)):
                    matched = False
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
                _logger.info('%s: `%s` handler matched!', operation_subgroup.hash, handler_config.callback)

                args = prepare_operation_handler_args(handler_config, matched_operations)
                matched_handlers.append((operation_subgroup, handler_config, args))

                matched_operations.clear()
                pattern_index = 0

        if len(matched_operations) >= sum(0 if x.optional else 1 for x in handler_config.pattern):
            _logger.info('%s: `%s` handler matched!', operation_subgroup.hash, handler_config.callback)

            args = prepare_operation_handler_args(handler_config, matched_operations)
            matched_handlers.append((operation_subgroup, handler_config, args))

    return matched_handlers
