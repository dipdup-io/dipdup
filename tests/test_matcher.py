"""Unit tests for tezos.operations matcher optional pattern items (see #1279)."""

from collections import deque
from datetime import UTC
from datetime import datetime

from dipdup.config.tezos_operations import TezosOperationsHandlerConfig
from dipdup.config.tezos_operations import TezosOperationsHandlerTransactionPatternConfig
from dipdup.indexes.tezos_operations.matcher import OperationSubgroup
from dipdup.indexes.tezos_operations.matcher import match_operation_subgroup
from dipdup.indexes.tezos_operations.matcher import prepare_operation_handler_args
from dipdup.models.tezos import TezosOperationData


def _make_operation(op_id: int, entrypoint: str = 'default') -> TezosOperationData:
    return TezosOperationData(
        type='transaction',
        id=op_id,
        level=1,
        timestamp=datetime.now(UTC),
        hash='ooTest',
        counter=1,
        sender_address='tz1abc',
        target_address='KT1abc',
        initiator_address=None,
        amount=1,
        status='applied',
        has_internals=False,
        storage=None,
        block='BL',
        sender_alias=None,
        nonce=None,
        target_alias=None,
        initiator_alias=None,
        entrypoint=entrypoint,
        parameter_json=None,
        originated_contract_address=None,
        originated_contract_alias=None,
        originated_contract_type_hash=None,
        originated_contract_code_hash=None,
        originated_contract_tzips=None,
        delegate_address=None,
        delegate_alias=None,
        target_code_hash=None,
        sender_code_hash=None,
    )


def _make_handler(
    *optionals: bool,
    entrypoints: tuple[str | None, ...] | None = None,
) -> TezosOperationsHandlerConfig:
    patterns = []
    for i, optional in enumerate(optionals):
        kwargs: dict = {'optional': optional}
        if entrypoints and entrypoints[i]:
            kwargs['entrypoint'] = entrypoints[i]
        patterns.append(TezosOperationsHandlerTransactionPatternConfig(**kwargs))
    return TezosOperationsHandlerConfig(
        callback='on_test',
        pattern=tuple(patterns),
    )


def test_prepare_pads_missing_optional_with_none() -> None:
    """A handler with a trailing optional pattern item must receive None for it (see #1279)."""
    handler_config = _make_handler(False, True)
    operation = _make_operation(1)

    args = prepare_operation_handler_args(None, handler_config, deque([operation]))

    assert len(args) == 2
    assert args[0] is operation
    assert args[1] is None


def test_match_passes_none_for_missing_trailing_optional() -> None:
    """End-to-end: the optional transaction is missing from the subgroup, the handler still fires with None."""
    handler_config = _make_handler(False, True)
    operation = _make_operation(1)
    subgroup = OperationSubgroup(hash='ooTest', counter=1, operations=(operation,))

    matched = match_operation_subgroup(None, [handler_config], subgroup)

    assert matched
    _, args = matched[0]
    assert len(args) == 2
    assert args[0] is operation
    assert args[1] is None


def test_match_passes_none_for_missing_optional_in_middle() -> None:
    """A missing optional pattern item in the middle of the pattern is passed as None."""
    handler_config = _make_handler(True, False, entrypoints=('transfer', 'default'))
    operation = _make_operation(1)
    subgroup = OperationSubgroup(hash='ooTest', counter=1, operations=(operation,))

    matched = match_operation_subgroup(None, [handler_config], subgroup)

    assert matched
    _, args = matched[0]
    assert len(args) == 2
    assert args[0] is None
    assert args[1] is operation


def test_match_without_optionals_unchanged() -> None:
    """Handlers without optional pattern items receive exactly the matched operations."""
    handler_config = _make_handler(False, False)
    first, second = _make_operation(1), _make_operation(2)
    subgroup = OperationSubgroup(hash='ooTest', counter=1, operations=(first, second))

    matched = match_operation_subgroup(None, [handler_config], subgroup)

    assert matched
    _, args = matched[0]
    assert tuple(args) == (first, second)
