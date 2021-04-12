from os.path import dirname, join
from typing import Callable, Type
from unittest import IsolatedAsyncioTestCase

from tortoise import Tortoise

from dipdup.config import DipDupConfig


class ConfigTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.path = join(dirname(__file__), 'dipdup.yml')

    async def test_load_initialize(self):
        config = DipDupConfig.load(self.path)

        try:
            await Tortoise.init(
                db_url='sqlite://:memory:',
                modules={
                    'int_models': ['dipdup.models'],
                },
            )
            await Tortoise.generate_schemas()
            await config.initialize()
        finally:
            await Tortoise.close_connections()

        self.assertIsInstance(config, DipDupConfig)
        self.assertEqual(
            config.contracts['HEN_minter'],
            config.indexes['hen_mainnet'].handlers[0].pattern[0].destination,
        )
        self.assertIsInstance(config.indexes['hen_mainnet'].handlers[0].callback_fn, Callable)
        self.assertIsInstance(config.indexes['hen_mainnet'].handlers[0].pattern[0].parameter_type_cls, Type)
