import json
from os.path import dirname, join
from unittest import TestCase, IsolatedAsyncioTestCase

from pytezos_dapps.config import PytezosDappConfig, OperationIndexConfig
from pytezos_dapps.datasources.tzkt.cache import OperationCache, OperationGroup
from pytezos_dapps.datasources.tzkt.datasource import TzktDatasource
from pytezos_dapps.models import OperationData


class TzktDatasourceTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.config = OperationIndexConfig(datasource='', contract='', handlers=[])
        self.cache = OperationCache(self.config, 0)

    async def test_add(self):
        with open(join(dirname(__file__), 'operations.json')) as file:
            operations_message = json.load(file)

        operations = [TzktDatasource.convert_operation(operation_json) for operation_json in operations_message['data']]
        await self.cache.add(operations[0])
        await self.cache.add(operations[1])

        expected_key = OperationGroup(hash='opGZHyGpDt6c8x2mKexrhc8btiMkuyF1EHeL3hQvaNtTxsyzUGu', counter=7057537)

        self.assertEqual(
            [expected_key],
            list(self.cache._operations.keys())
        )
        self.assertEqual(2, len(self.cache._operations[expected_key]))
