import pytest

from dipdup.config.tezos import TezosContractConfig
from dipdup.config.tezos_tzkt_operations import OperationsHandlerOriginationPatternConfig
from dipdup.config.tezos_tzkt_operations import OperationsHandlerTransactionPatternConfig


@pytest.fixture
def contract() -> TezosContractConfig:
    contract = TezosContractConfig(kind='tezos', address='KT1Hkg5qeCgJPwE6SDh8KKPDiun7j5G8r4ee')
    contract._name = 'dex_contract'
    return contract


def test_transaction_callbacks(contract: TezosContractConfig) -> None:
    # NOTE: Typed `transaction`
    pattern = OperationsHandlerTransactionPatternConfig(
        destination=contract,
        entrypoint='fooBar',
    )
    assert tuple(pattern.iter_arguments()) == (('foo_bar', 'TzktTransaction[FooBarParameter, DexContractStorage]'),)
    assert tuple(pattern.iter_imports('test')) == (
        ('dipdup.models.tezos_tzkt', 'TzktTransaction'),
        ('test.types.dex_contract.tezos_parameters.foo_bar', 'FooBarParameter'),
        ('test.types.dex_contract.tezos_storage', 'DexContractStorage'),
    )

    # NOTE: With alias and optional
    pattern.alias = 'aliased'
    pattern.optional = True

    assert tuple(pattern.iter_arguments()) == (
        ('aliased', 'TzktTransaction[AliasedParameter, DexContractStorage] | None'),
    )
    assert tuple(pattern.iter_imports('test')) == (
        ('dipdup.models.tezos_tzkt', 'TzktTransaction'),
        ('test.types.dex_contract.tezos_parameters.foo_bar', 'FooBarParameter as AliasedParameter'),
        ('test.types.dex_contract.tezos_storage', 'DexContractStorage'),
    )

    # NOTE: Untyped `transaction`
    pattern = OperationsHandlerTransactionPatternConfig(
        destination=contract,
    )
    pattern.subgroup_index = 1
    assert tuple(pattern.iter_arguments()) == (('transaction_1', 'TzktOperationData'),)
    assert tuple(pattern.iter_imports('test')) == (('dipdup.models.tezos_tzkt', 'TzktOperationData'),)

    # NOTE: With alias and optional
    pattern.alias = 'aliased'
    pattern.optional = True

    assert tuple(pattern.iter_arguments()) == (('aliased', 'TzktOperationData | None'),)
    assert tuple(pattern.iter_imports('test')) == (('dipdup.models.tezos_tzkt', 'TzktOperationData'),)


def test_origination_callbacks(contract: TezosContractConfig) -> None:
    # NOTE: Typed `origination`
    pattern = OperationsHandlerOriginationPatternConfig(
        originated_contract=contract,
    )
    assert tuple(pattern.iter_arguments()) == (('dex_contract_origination', 'TzktOrigination[DexContractStorage]'),)
    assert tuple(pattern.iter_imports('test')) == (
        ('dipdup.models.tezos_tzkt', 'TzktOrigination'),
        ('test.types.dex_contract.tezos_storage', 'DexContractStorage'),
    )

    # NOTE: With alias and optional
    pattern.alias = 'aliased'
    pattern.optional = True

    assert tuple(pattern.iter_arguments()) == (('aliased', 'TzktOrigination[DexContractStorage] | None'),)
    assert tuple(pattern.iter_imports('test')) == (
        ('dipdup.models.tezos_tzkt', 'TzktOrigination'),
        ('test.types.dex_contract.tezos_storage', 'DexContractStorage'),
    )

    # NOTE: Untyped `origination`
    pattern = OperationsHandlerOriginationPatternConfig(
        source=contract,
    )
    pattern.subgroup_index = 1
    assert tuple(pattern.iter_arguments()) == (('origination_1', 'TzktOperationData'),)
    assert tuple(pattern.iter_imports('test')) == (('dipdup.models.tezos_tzkt', 'TzktOperationData'),)

    # NOTE: With alias and optional
    pattern.alias = 'aliased'
    pattern.optional = True

    assert tuple(pattern.iter_arguments()) == (('aliased', 'TzktOperationData | None'),)
    assert tuple(pattern.iter_imports('test')) == (('dipdup.models.tezos_tzkt', 'TzktOperationData'),)
