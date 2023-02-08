import pytest

from dipdup.config import ContractConfig
from dipdup.config.tezos_tzkt_operations import OperationsHandlerOriginationPatternConfig
from dipdup.config.tezos_tzkt_operations import OperationsHandlerTransactionPatternConfig


@pytest.fixture
def contract() -> ContractConfig:
    contract = ContractConfig(address='KT1Hkg5qeCgJPwE6SDh8KKPDiun7j5G8r4ee')
    contract._name = 'dex_contract'
    return contract


def test_transaction_callbacks(contract: ContractConfig) -> None:
    # NOTE: Typed `transaction`
    pattern = OperationsHandlerTransactionPatternConfig(
        destination=contract,
        entrypoint='fooBar',
    )
    assert tuple(pattern.iter_arguments()) == (('foo_bar', 'Transaction[FooBarParameter, DexContractStorage]'),)
    assert tuple(pattern.iter_imports('test')) == (
        ('dipdup.models.tezos_tzkt', 'Transaction'),
        ('test.types.dex_contract.parameter.foo_bar', 'FooBarParameter'),
        ('test.types.dex_contract.storage', 'DexContractStorage'),
    )

    # NOTE: With alias and optional
    pattern.alias = 'aliased'
    pattern.optional = True

    assert tuple(pattern.iter_arguments()) == (('aliased', 'Transaction[AliasedParameter, DexContractStorage] | None'),)
    assert tuple(pattern.iter_imports('test')) == (
        ('dipdup.models.tezos_tzkt', 'Transaction'),
        ('test.types.dex_contract.parameter.foo_bar', 'FooBarParameter as AliasedParameter'),
        ('test.types.dex_contract.storage', 'DexContractStorage'),
    )

    # NOTE: Untyped `transaction`
    pattern = OperationsHandlerTransactionPatternConfig(
        destination=contract,
    )
    pattern.subgroup_index = 1
    assert tuple(pattern.iter_arguments()) == (('transaction_1', 'OperationData'),)
    assert tuple(pattern.iter_imports('test')) == (('dipdup.models.tezos_tzkt', 'OperationData'),)

    # NOTE: With alias and optional
    pattern.alias = 'aliased'
    pattern.optional = True

    assert tuple(pattern.iter_arguments()) == (('aliased', 'OperationData | None'),)
    assert tuple(pattern.iter_imports('test')) == (('dipdup.models.tezos_tzkt', 'OperationData'),)


def test_origination_callbacks(contract: ContractConfig) -> None:

    # NOTE: Typed `origination`
    pattern = OperationsHandlerOriginationPatternConfig(
        originated_contract=contract,
    )
    assert tuple(pattern.iter_arguments()) == (('dex_contract_origination', 'Origination[DexContractStorage]'),)
    assert tuple(pattern.iter_imports('test')) == (
        ('dipdup.models.tezos_tzkt', 'Origination'),
        ('test.types.dex_contract.storage', 'DexContractStorage'),
    )

    # NOTE: With alias and optional
    pattern.alias = 'aliased'
    pattern.optional = True

    assert tuple(pattern.iter_arguments()) == (('aliased', 'Origination[DexContractStorage] | None'),)
    assert tuple(pattern.iter_imports('test')) == (
        ('dipdup.models.tezos_tzkt', 'Origination'),
        ('test.types.dex_contract.storage', 'DexContractStorage'),
    )

    # NOTE: Untyped `origination`
    pattern = OperationsHandlerOriginationPatternConfig(
        source=contract,
    )
    pattern.subgroup_index = 1
    assert tuple(pattern.iter_arguments()) == (('origination_1', 'OperationData'),)
    assert tuple(pattern.iter_imports('test')) == (('dipdup.models.tezos_tzkt', 'OperationData'),)

    # NOTE: With alias and optional
    pattern.alias = 'aliased'
    pattern.optional = True

    assert tuple(pattern.iter_arguments()) == (('aliased', 'OperationData | None'),)
    assert tuple(pattern.iter_imports('test')) == (('dipdup.models.tezos_tzkt', 'OperationData'),)
