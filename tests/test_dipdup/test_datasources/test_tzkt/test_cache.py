import json
from datetime import datetime
from os.path import dirname, join
from unittest.async_case import IsolatedAsyncioTestCase  # type: ignore
from unittest.mock import ANY, AsyncMock  # type: ignore

from dateutil.tz import tzutc

from dipdup.config import OperationHandlerConfig, OperationHandlerPatternConfig, OperationIndexConfig
from dipdup.datasources.tzkt.cache import OperationCache, OperationGroup
from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.models import OperationData


class TzktDatasourceTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.config = OperationIndexConfig(
            datasource='',
            contract='',
            handlers=[
                OperationHandlerConfig(
                    callback='',
                    pattern=[OperationHandlerPatternConfig(destination='KT1AFA2mwNUMNd4SsujE1YYp29vd8BZejyKW', entrypoint='hDAO_batch')],
                )
            ],
        )
        self.cache = OperationCache(self.config, 0)

    async def test_add(self):
        with open(join(dirname(__file__), 'operations.json')) as file:
            operations_message = json.load(file)

        operations = [TzktDatasource.convert_operation(operation_json) for operation_json in operations_message['data']]
        await self.cache.add(operations[0])
        await self.cache.add(operations[1])

        expected_key = OperationGroup(hash='opGZHyGpDt6c8x2mKexrhc8btiMkuyF1EHeL3hQvaNtTxsyzUGu', counter=7057537)

        self.assertEqual([expected_key], list(self.cache._operations.keys()))
        self.assertEqual(2, len(self.cache._operations[expected_key]))

    async def test_process(self):
        callback_mock = AsyncMock()

        with open(join(dirname(__file__), 'operations.json')) as file:
            operations_message = json.load(file)

        operations = [TzktDatasource.convert_operation(operation_json) for operation_json in operations_message['data']]
        for operation in operations:
            await self.cache.add(operation)

        await self.cache.process(callback_mock)

        callback_mock.assert_awaited_with(
            OperationHandlerConfig(
                callback='',
                pattern=[OperationHandlerPatternConfig(destination='KT1AFA2mwNUMNd4SsujE1YYp29vd8BZejyKW', entrypoint='hDAO_batch')],
            ),
            [
                OperationData(
                    type='transaction',
                    id=44184277,
                    level=1405375,
                    timestamp=datetime(2021, 3, 29, 5, 51, 44, tzinfo=tzutc()),
                    block='BMZunRxN8A3tsNHhEFtN2Yb5ArX7Ls8KGbGTy1svoPbLNQRDA8H',
                    hash='opDvkDvtCoKhefWZSz7nQ46tUYxyScqa5Ex5HbiLsbEn2BiKMis',
                    counter=8895059,
                    initiator_address='tz1YRG68NdqtAcsFEwTUw6FsSsiBb5kagEDo',
                    sender_address='KT1Hkg5qeNhfwpKW4fXvq7HGZB9z2EnmCCA9',
                    sender_alias='Hic et nunc Minter',
                    nonce=8,
                    gas_limit=0,
                    gas_used=29590,
                    storage_limit=0,
                    storage_used=0,
                    baker_fee=0,
                    storage_fee=0,
                    allocation_fee=0,
                    target_alias='hDAO',
                    target_address='KT1AFA2mwNUMNd4SsujE1YYp29vd8BZejyKW',
                    amount=0,
                    entrypoint='hDAO_batch',
                    parameter_json=[
                        {'to_': 'tz1YRG68NdqtAcsFEwTUw6FsSsiBb5kagEDo', 'amount': '500000'},
                        {'to_': 'tz1ZsNvZKUveN7FjRhMHTm9NiAUNAmrwdFKV', 'amount': '500000'},
                        {'to_': 'tz1UBZUkXpKGhYsP5KtzDNqLLchwF4uHrGjw', 'amount': '25000'},
                    ],
                    status='applied',
                    has_internals=False,
                    parameter="{'entrypoint': 'hDAO_batch', 'value': [{'to_': 'tz1YRG68NdqtAcsFEwTUw6FsSsiBb5kagEDo', 'amount': '500000'}, {'to_': 'tz1ZsNvZKUveN7FjRhMHTm9NiAUNAmrwdFKV', 'amount': '500000'}, {'to_': 'tz1UBZUkXpKGhYsP5KtzDNqLLchwF4uHrGjw', 'amount': '25000'}]}",
                )
            ],
            ANY,
        )
