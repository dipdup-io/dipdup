import tempfile
from pathlib import Path
from typing import Callable
from typing import Type

import pytest

from dipdup.config import ContractConfig
from dipdup.config import DipDupConfig
from dipdup.config import HasuraConfig
from dipdup.config import PostgresDatabaseConfig
from dipdup.config import TzktDatasourceConfig
from dipdup.datasources.tzkt.models import OriginationSubscription
from dipdup.datasources.tzkt.models import TransactionSubscription
from dipdup.enums import OperationType
from dipdup.exceptions import ConfigurationError


def create_config(merge_subs: bool = False, origs: bool = False) -> DipDupConfig:
    path = Path(__file__).parent.parent / 'configs' / 'dipdup.yml'
    config = DipDupConfig.load([path])
    config.advanced.merge_subscriptions = merge_subs
    if origs:
        config.indexes['hen_mainnet'].types += (OperationType.origination,)  # type: ignore[union-attr]
    config.initialize()
    return config


async def test_load_initialize() -> None:
    config = create_config()

    assert isinstance(config, DipDupConfig)
    destination = config.indexes['hen_mainnet'].handlers[0].pattern[0].destination  # type: ignore
    assert destination == config.contracts['HEN_minter']
    assert isinstance(config.indexes['hen_mainnet'].handlers[0].callback_fn, Callable)  # type: ignore
    assert isinstance(config.indexes['hen_mainnet'].handlers[0].pattern[0].parameter_type_cls, Type)  # type: ignore


async def test_operation_subscriptions() -> None:
    config = create_config(False, False)
    assert config.indexes['hen_mainnet'].subscriptions == {  # type: ignore
        TransactionSubscription(address='KT1Hkg5qeNhfwpKW4fXvq7HGZB9z2EnmCCA9')
    }

    config = create_config(True, False)
    assert config.indexes['hen_mainnet'].subscriptions == {TransactionSubscription()}  # type: ignore

    config = create_config(False, True)
    assert config.indexes['hen_mainnet'].subscriptions == {TransactionSubscription(address='KT1Hkg5qeNhfwpKW4fXvq7HGZB9z2EnmCCA9'), OriginationSubscription()}  # type: ignore

    config = create_config(True, True)
    assert config.indexes['hen_mainnet'].subscriptions == {TransactionSubscription(), OriginationSubscription()}  # type: ignore


async def test_validators() -> None:
    with pytest.raises(ConfigurationError):
        ContractConfig(address='KT1lalala')
    with pytest.raises(ConfigurationError):
        ContractConfig(address='lalalalalalalalalalalalalalalalalala')
    with pytest.raises(ConfigurationError):
        TzktDatasourceConfig(kind='tzkt', url='not_an_url')


async def test_dump() -> None:
    config = create_config()

    tmp = tempfile.mkstemp()[1]
    with open(tmp, 'w') as f:
        f.write(config.dump())

    config = DipDupConfig.load([Path(tmp)], environment=False)
    config.initialize()


async def test_secrets() -> None:
    db_config = PostgresDatabaseConfig(
        kind='postgres',
        host='localhost',
        password='SeCrEt=)',
    )
    hasura_config = HasuraConfig(
        url='https://localhost',
        admin_secret='SeCrEt=)',
    )
    assert 'localhost' in str(db_config)
    assert 'SeCrEt=)' not in str(db_config)
    assert 'localhost' in str(hasura_config)
    assert 'SeCrEt=)' not in str(hasura_config)
