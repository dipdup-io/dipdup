import tempfile
from pathlib import Path
from typing import Callable
from typing import Type
from unittest import IsolatedAsyncioTestCase

from dipdup.config import ContractConfig
from dipdup.config import DipDupConfig
from dipdup.config import HasuraConfig
from dipdup.config import PostgresDatabaseConfig
from dipdup.config import TzktDatasourceConfig
from dipdup.datasources.tzkt.models import OriginationSubscription
from dipdup.datasources.tzkt.models import TransactionSubscription
from dipdup.enums import OperationType
from dipdup.exceptions import ConfigurationError


class ConfigTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.path = Path(__file__).parent / 'dipdup.yml'

    async def test_load_initialize(self) -> None:
        config = DipDupConfig.load([self.path])

        config.initialize()

        self.assertIsInstance(config, DipDupConfig)
        self.assertEqual(
            config.contracts['HEN_minter'],
            config.indexes['hen_mainnet'].handlers[0].pattern[0].destination,
        )
        self.assertIsInstance(config.indexes['hen_mainnet'].handlers[0].callback_fn, Callable)
        self.assertIsInstance(config.indexes['hen_mainnet'].handlers[0].pattern[0].parameter_type_cls, Type)

    async def test_subscriptions(self) -> None:
        config = DipDupConfig.load([self.path])
        config.advanced.merge_subscriptions = False
        config.initialize()

        self.assertEqual(
            {TransactionSubscription(address='KT1Hkg5qeNhfwpKW4fXvq7HGZB9z2EnmCCA9')},
            config.indexes['hen_mainnet'].subscriptions,  # type: ignore
        )

        config = DipDupConfig.load([self.path])
        config.advanced.merge_subscriptions = True
        config.initialize()

        self.assertEqual(
            {TransactionSubscription()},
            config.indexes['hen_mainnet'].subscriptions,  # type: ignore
        )

        config = DipDupConfig.load([self.path])
        config.indexes['hen_mainnet'].types = config.indexes['hen_mainnet'].types + (OperationType.origination,)  # type: ignore
        config.initialize()

        self.assertEqual(
            {TransactionSubscription(), OriginationSubscription()},
            config.indexes['hen_mainnet'].subscriptions,  # type: ignore
        )

    async def test_validators(self) -> None:
        with self.assertRaises(ConfigurationError):
            ContractConfig(address='KT1lalala')
        with self.assertRaises(ConfigurationError):
            ContractConfig(address='lalalalalalalalalalalalalalalalalala')
        with self.assertRaises(ConfigurationError):
            TzktDatasourceConfig(kind='tzkt', url='not_an_url')

    async def test_dump(self) -> None:
        config = DipDupConfig.load([self.path])
        config.initialize()

        tmp = tempfile.mkstemp()[1]
        with open(tmp, 'w') as f:
            f.write(config.dump())

        config = DipDupConfig.load([tmp], environment=False)
        config.initialize()

    async def test_secrets(self) -> None:
        db_config = PostgresDatabaseConfig(
            kind='postgres',
            host='localhost',
            password='SeCrEt=)',
        )
        hasura_config = HasuraConfig(
            url='https://localhost',
            admin_secret='SeCrEt=)',
        )
        self.assertIn('localhost', str(db_config))
        self.assertNotIn('SeCrEt=)', str(db_config))
        self.assertIn('localhost', str(db_config))
        self.assertNotIn('SeCrEt=)', str(hasura_config))
