import tempfile
from os.path import dirname
from os.path import join
from typing import Callable
from typing import Type
from unittest import IsolatedAsyncioTestCase

from dipdup.config import ContractConfig
from dipdup.config import DipDupConfig
from dipdup.config import TzktDatasourceConfig
from dipdup.datasources.subscription import OriginationSubscription
from dipdup.datasources.subscription import TransactionSubscription
from dipdup.enums import OperationType
from dipdup.exceptions import ConfigurationError


class ConfigTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.path = join(dirname(__file__), 'dipdup.yml')

    async def test_load_initialize(self):
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

    async def test_validators(self):
        with self.assertRaises(ConfigurationError):
            ContractConfig(address='KT1lalala')
        with self.assertRaises(ConfigurationError):
            ContractConfig(address='lalalalalalalalalalalalalalalalalala')
        with self.assertRaises(ConfigurationError):
            TzktDatasourceConfig(kind='tzkt', url='not_an_url')

    async def test_dump(self):
        config = DipDupConfig.load([self.path])
        config.initialize()

        tmp = tempfile.mkstemp()[1]
        with open(tmp, 'w') as f:
            f.write(config.dump())

        config = DipDupConfig.load([tmp], environment=False)
        config.initialize()
