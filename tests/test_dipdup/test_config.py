import tempfile
from os.path import dirname
from os.path import join
from typing import Callable
from typing import Type
from unittest import IsolatedAsyncioTestCase

from dipdup.config import ContractConfig
from dipdup.config import DipDupConfig
from dipdup.config import TzktDatasourceConfig
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
