import pytest

from dipdup.config.tezos import TezosContractConfig
from dipdup.config.tezos_operations import TezosOperationsHandlerOriginationPatternConfig
from dipdup.config.tezos_operations import TezosOperationsHandlerTransactionPatternConfig


@pytest.fixture
def contract() -> TezosContractConfig:
    contract = TezosContractConfig(kind='tezos', address='KT1Hkg5qeCgJPwE6SDh8KKPDiun7j5G8r4ee')
    contract._name = 'dex_contract'
    return contract


def test_transaction_callbacks(contract: TezosContractConfig) -> None:
    # NOTE: Typed `transaction`
    pattern = TezosOperationsHandlerTransactionPatternConfig(
        destination=contract,
        entrypoint='fooBar',
    )
    assert tuple(pattern.iter_arguments()) == (('foo_bar', 'TezosTransaction[FooBarParameter, DexContractStorage]'),)
    assert tuple(pattern.iter_imports('test')) == (
        ('dipdup.models.tezos', 'TezosTransaction'),
        ('test.types.dex_contract.tezos_parameters.foo_bar', 'FooBarParameter'),
        ('test.types.dex_contract.tezos_storage', 'DexContractStorage'),
    )

    # NOTE: With alias and optional
    pattern.alias = 'aliased'
    pattern.optional = True

    assert tuple(pattern.iter_arguments()) == (
        ('aliased', 'TezosTransaction[AliasedParameter, DexContractStorage] | None'),
    )
    assert tuple(pattern.iter_imports('test')) == (
        ('dipdup.models.tezos', 'TezosTransaction'),
        ('test.types.dex_contract.tezos_parameters.foo_bar', 'FooBarParameter as AliasedParameter'),
        ('test.types.dex_contract.tezos_storage', 'DexContractStorage'),
    )

    # NOTE: Untyped `transaction`
    pattern = TezosOperationsHandlerTransactionPatternConfig(
        destination=contract,
    )
    pattern.subgroup_index = 1
    assert tuple(pattern.iter_arguments()) == (('transaction_1', 'TezosOperationData'),)
    assert tuple(pattern.iter_imports('test')) == (('dipdup.models.tezos', 'TezosOperationData'),)

    # NOTE: With alias and optional
    pattern.alias = 'aliased'
    pattern.optional = True

    assert tuple(pattern.iter_arguments()) == (('aliased', 'TezosOperationData | None'),)
    assert tuple(pattern.iter_imports('test')) == (('dipdup.models.tezos', 'TezosOperationData'),)


def test_origination_callbacks(contract: TezosContractConfig) -> None:
    # NOTE: Typed `origination`
    pattern = TezosOperationsHandlerOriginationPatternConfig(
        originated_contract=contract,
    )
    assert tuple(pattern.iter_arguments()) == (('dex_contract_origination', 'TezosOrigination[DexContractStorage]'),)
    assert tuple(pattern.iter_imports('test')) == (
        ('dipdup.models.tezos', 'TezosOrigination'),
        ('test.types.dex_contract.tezos_storage', 'DexContractStorage'),
    )

    # NOTE: With alias and optional
    pattern.alias = 'aliased'
    pattern.optional = True

    assert tuple(pattern.iter_arguments()) == (('aliased', 'TezosOrigination[DexContractStorage] | None'),)
    assert tuple(pattern.iter_imports('test')) == (
        ('dipdup.models.tezos', 'TezosOrigination'),
        ('test.types.dex_contract.tezos_storage', 'DexContractStorage'),
    )

    # NOTE: Untyped `origination`
    pattern = TezosOperationsHandlerOriginationPatternConfig(
        source=contract,
    )
    pattern.subgroup_index = 1
    assert tuple(pattern.iter_arguments()) == (('origination_1', 'TezosOperationData'),)
    assert tuple(pattern.iter_imports('test')) == (('dipdup.models.tezos', 'TezosOperationData'),)

    # NOTE: With alias and optional
    pattern.alias = 'aliased'
    pattern.optional = True

    assert tuple(pattern.iter_arguments()) == (('aliased', 'TezosOperationData | None'),)
    assert tuple(pattern.iter_imports('test')) == (('dipdup.models.tezos', 'TezosOperationData'),)
