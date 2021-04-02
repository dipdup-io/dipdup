import json
from functools import partial
from os.path import dirname, join
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, call

from dipdup.config import OperationHandlerConfig, OperationHandlerPatternConfig, OperationIndexConfig
from signalrcore.hub.base_hub_connection import BaseHubConnection  # type: ignore

from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.models import OperationData, State
from signalrcore.transport.websockets.connection import ConnectionState


class TzktDatasourceTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.state = State(dapp='test')
        self.index_config = OperationIndexConfig(
            datasource='tzkt',
            contract='KT1lalala',
            handlers=[
                OperationHandlerConfig(
                    callback='',
                    pattern=[OperationHandlerPatternConfig(destination='KT1AFA2mwNUMNd4SsujE1YYp29vd8BZejyKW', entrypoint='hDAO_batch')],
                )
            ],
        )
        self.datasource = TzktDatasource('tzkt.test', self.index_config, self.state)

    async def test_convert_operation(self):
        with open(join(dirname(__file__), 'operations.json')) as file:
            operations_message = json.load(file)

        for operation_json in operations_message['data']:
            operation = TzktDatasource.convert_operation(operation_json)
            self.assertIsInstance(operation, OperationData)

    async def test_get_client(self):
        client = self.datasource._get_client()
        self.assertIsInstance(client, BaseHubConnection)
        self.assertEqual(self.datasource.on_connect, client.transport._on_open)

    async def test_start(self):
        client = self.datasource._get_client()
        client.start = AsyncMock()

        await self.datasource.start()

        self.assertEqual({self.index_config.contract: ['transaction']}, self.datasource._subscriptions)
        client.start.assert_awaited()

    async def test_on_connect_subscribe_to_operations(self):
        send_mock = AsyncMock()
        client = self.datasource._get_client()
        client.send = send_mock
        client.transport.state = ConnectionState.connected
        self.datasource._subscriptions = {
            self.index_config.contract: ['transaction'],
            'some_contract': ['transaction'],
        }

        await self.datasource.on_connect()

        send_mock.assert_has_awaits(
            [
                call('SubscribeToOperations', [{'address': self.index_config.contract, 'types': 'transaction'}]),
                call('SubscribeToOperations', [{'address': 'some_contract', 'types': 'transaction'}]),
            ]
        )
        self.assertEqual(2, len(client.handlers))
