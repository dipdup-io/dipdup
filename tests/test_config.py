import json
from os.path import dirname, join
from typing import Callable, Type
from unittest import TestCase
from pytezos_dapps.config import PytezosDappConfig

from pytezos_dapps.datasources.tzkt.datasource import TzktDatasource


class ConfigTest(TestCase):
    def setUp(self):
        self.path = join(dirname(__file__), 'config.yml')

    def test_load_initialize(self):
        config = PytezosDappConfig.load(self.path)
        config.initialize()

        self.assertIsInstance(config, PytezosDappConfig)
        self.assertEqual(
            config.contracts['HEN_objkts'].address,
            config.indexes['operations_mainnet'].operation.handlers[0].pattern[0].destination
        )
        self.assertIsInstance(config.indexes['operations_mainnet'].operation.handlers[0].callback_fn, Callable)
        self.assertIsInstance(config.indexes['operations_mainnet'].operation.handlers[0].pattern[0].parameter_type_cls, Type)
