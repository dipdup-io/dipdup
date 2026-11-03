from datetime import UTC
from datetime import datetime
from pathlib import Path

import pytest

from dipdup.config.tezos_operations import TezosOperationsHandlerConfig
from dipdup.config.tezos_operations import TezosOperationsHandlerTransactionPatternConfig as TransactionPattern
from dipdup.indexes.tezos_operations.matcher import OperationSubgroup
from dipdup.indexes.tezos_operations.matcher import TezosOperationsHandlerArgumentU
from dipdup.indexes.tezos_operations.matcher import match_operation_subgroup
from dipdup.models.tezos import TezosOperationData
from dipdup.package import DipDupPackage


@pytest.fixture
def package(tmp_path: Path) -> DipDupPackage:
    # NOTE: Untyped patterns below never read the package; a real empty one is enough.
    return DipDupPackage(tmp_path, quiet=True)


def transaction(id_: int, entrypoint: str) -> TezosOperationData:
    return TezosOperationData(
        type='transaction',
        id=id_,
        level=1,
        timestamp=datetime.now(UTC),
        hash='op',
        counter=1,
        sender_address=None,
        target_address=None,
        initiator_address=None,
        amount=0,
        status='applied',
        has_internals=False,
        storage=None,
        block=None,
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


def handler(callback: str, *pattern: TransactionPattern) -> TezosOperationsHandlerConfig:
    return TezosOperationsHandlerConfig(callback=callback, pattern=pattern)


def match(
    package: DipDupPackage,
    handlers: tuple[TezosOperationsHandlerConfig, ...],
    operations: tuple[TezosOperationData, ...],
    alt: bool = False,
) -> list[tuple[str, list[TezosOperationsHandlerArgumentU]]]:
    subgroup = OperationSubgroup(hash='op', counter=1, operations=operations)
    matched = match_operation_subgroup(package, handlers, subgroup, alt=alt)
    return [(config.callback, list(args)) for config, args in matched]


def test_trailing_optional_missing_is_none(package: DipDupPackage) -> None:
    a = transaction(1, 'a')
    on_ab = handler('on_ab', TransactionPattern(entrypoint='a'), TransactionPattern(entrypoint='b', optional=True))

    assert match(package, (on_ab,), (a,)) == [('on_ab', [a, None])]


def test_trailing_optionals_missing_are_none(package: DipDupPackage) -> None:
    a = transaction(1, 'a')
    on_abc = handler(
        'on_abc',
        TransactionPattern(entrypoint='a'),
        TransactionPattern(entrypoint='b', optional=True),
        TransactionPattern(entrypoint='c', optional=True),
    )

    assert match(package, (on_abc,), (a,)) == [('on_abc', [a, None, None])]


def test_middle_optional_missing_is_none(package: DipDupPackage) -> None:
    a, c = transaction(1, 'a'), transaction(2, 'c')
    on_abc = handler(
        'on_abc',
        TransactionPattern(entrypoint='a'),
        TransactionPattern(entrypoint='b', optional=True),
        TransactionPattern(entrypoint='c'),
    )

    assert match(package, (on_abc,), (a, c)) == [('on_abc', [a, None, c])]


def test_required_tail_missing_does_not_match(package: DipDupPackage) -> None:
    a, b = transaction(1, 'a'), transaction(2, 'b')
    on_abc = handler(
        'on_abc',
        TransactionPattern(entrypoint='a'),
        TransactionPattern(entrypoint='b', optional=True),
        TransactionPattern(entrypoint='c'),
    )

    assert match(package, (on_abc,), (a, b)) == []


def test_all_optional_pattern_without_matches_is_not_called(package: DipDupPackage) -> None:
    x = transaction(1, 'x')
    on_ab = handler(
        'on_ab',
        TransactionPattern(entrypoint='a', optional=True),
        TransactionPattern(entrypoint='b', optional=True),
    )

    assert match(package, (on_ab,), (x,)) == []


def test_all_optional_pattern_matches_once(package: DipDupPackage) -> None:
    x, b = transaction(1, 'x'), transaction(2, 'b')
    on_ab = handler(
        'on_ab',
        TransactionPattern(entrypoint='a', optional=True),
        TransactionPattern(entrypoint='b', optional=True),
    )

    assert match(package, (on_ab,), (x, b)) == [('on_ab', [None, b])]


def test_required_pattern(package: DipDupPackage) -> None:
    a1, b1, x, a2, b2 = (transaction(i, e) for i, e in enumerate(('a', 'b', 'x', 'a', 'b')))
    on_ab = handler('on_ab', TransactionPattern(entrypoint='a'), TransactionPattern(entrypoint='b'))

    assert match(package, (on_ab,), (a1, b1, x, a2, b2)) == [('on_ab', [a1, b1]), ('on_ab', [a2, b2])]
    assert match(package, (on_ab,), (a1, x)) == []


def test_alt_matcher_with_trailing_none(package: DipDupPackage) -> None:
    a = transaction(1, 'a')
    on_ab = handler('on_ab', TransactionPattern(entrypoint='a'), TransactionPattern(entrypoint='b', optional=True))

    assert match(package, (on_ab,), (a,), alt=True) == [('on_ab', [a, None])]
