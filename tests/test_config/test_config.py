import tempfile
from pathlib import Path
from typing import Callable

import pytest
from pydantic import ValidationError

from dipdup.config import ContractConfig
from dipdup.config import DipDupConfig
from dipdup.config import HasuraConfig
from dipdup.config import OperationIndexConfig
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
    index_config = config.indexes['hen_mainnet']
    assert isinstance(index_config, OperationIndexConfig)

    assert isinstance(config, DipDupConfig)
    destination = index_config.handlers[0].pattern[0].destination  # type: ignore[union-attr]
    assert destination == config.contracts['HEN_minter']
    assert isinstance(index_config.handlers[0].callback_fn, Callable)  # type: ignore[arg-type]
    assert isinstance(index_config.handlers[0].pattern[0].parameter_type_cls, type)  # type: ignore[union-attr]


async def test_operation_subscriptions() -> None:
    index_config = create_config(False, False).indexes['hen_mainnet']
    assert isinstance(index_config, OperationIndexConfig)
    assert index_config.subscriptions == {TransactionSubscription(address='KT1Hkg5qeNhfwpKW4fXvq7HGZB9z2EnmCCA9')}

    index_config = create_config(True, False).indexes['hen_mainnet']
    assert isinstance(index_config, OperationIndexConfig)
    assert index_config.subscriptions == {TransactionSubscription()}

    index_config = create_config(False, True).indexes['hen_mainnet']
    assert isinstance(index_config, OperationIndexConfig)
    assert index_config.subscriptions == {
        TransactionSubscription(address='KT1Hkg5qeNhfwpKW4fXvq7HGZB9z2EnmCCA9'),
        OriginationSubscription(),
    }

    index_config = create_config(True, True).indexes['hen_mainnet']
    assert isinstance(index_config, OperationIndexConfig)
    assert index_config.subscriptions == {TransactionSubscription(), OriginationSubscription()}


async def test_validators() -> None:
    # NOTE: @validator wrapped with `ConfigurationError` in `DipDupConfig.load`
    with pytest.raises(ValidationError):
        ContractConfig(address='KT1lalala')
    with pytest.raises(ValidationError):
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
