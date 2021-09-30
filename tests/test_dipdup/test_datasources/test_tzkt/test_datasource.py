import json
from os.path import dirname, join
from unittest import IsolatedAsyncioTestCase, skip
from unittest.mock import ANY, AsyncMock, MagicMock, call, patch

from aiosignalrcore.hub.base_hub_connection import BaseHubConnection  # type: ignore
from aiosignalrcore.transport.websockets.connection import ConnectionState  # type: ignore
from tortoise import Tortoise

from demo_hic_et_nunc.types.hen_minter.parameter.collect import CollectParameter
from demo_registrydao.types.registry.parameter.propose import ProposeParameter
from demo_registrydao.types.registry.storage import Proposals, RegistryStorage
from dipdup.config import (
    ContractConfig,
    OperationHandlerConfig,
    OperationHandlerTransactionPatternConfig,
    OperationIndexConfig,
    OperationType,
)
from dipdup.context import HandlerContext
from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.dipdup import DipDup
from dipdup.models import Index as State
from dipdup.models import IndexType, OperationData, Transaction
from dipdup.utils.database import tortoise_wrapper


@skip('FIXME')
class TzktDatasourceTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.index_config = OperationIndexConfig(
            kind='operation',
            datasource='tzkt',
            contracts=[ContractConfig(address='KT1Hkg5qeNhfwpKW4fXvq7HGZB9z2EnmCCA9')],
            handlers=[
                OperationHandlerConfig(
                    callback='',
                    pattern=[
                        OperationHandlerTransactionPatternConfig(
                            type='transaction',
                            destination=ContractConfig(address='KT1Hkg5qeNhfwpKW4fXvq7HGZB9z2EnmCCA9'),
                            entrypoint='collect',
                        )
                    ],
                )
            ],
        )
        self.index_config.state = State(name='test', type=IndexType.operation, hash='')
        self.index_config.handlers[0].pattern[0].parameter_type_cls = CollectParameter
        self.dipdup_mock = MagicMock(spec=DipDup)
        self.datasource = TzktDatasource('tzkt.test', self.dipdup_mock)
        await self.datasource.add_index('test', self.index_config)

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

        fetch_operations_mock = AsyncMock()
        self.datasource.fetch_operations = fetch_operations_mock

        get_mock = MagicMock()
        get_mock.return_value.__aenter__.return_value.json.return_value = {'level': 1337}

        with patch('aiohttp.ClientSession.get', get_mock):
            await self.datasource.start()

        fetch_operations_mock.assert_awaited_with(self.index_config, 1337)
        self.assertEqual({self.index_config.contracts[0].address: [OperationType.transaction]}, self.datasource._transaction_subscriptions)
        client.start.assert_awaited()

    async def test_on_connect_subscribe_to_operations(self):
        send_mock = AsyncMock()
        client = self.datasource._get_client()
        client.send = send_mock
        client.transport.state = ConnectionState.connected
        self.datasource._transaction_subscriptions = {
            self.index_config.contracts[0].address: [OperationType.transaction],
        }

        await self.datasource.on_connect()

        send_mock.assert_has_awaits(
            [
                call('SubscribeToOperations', [{'address': self.index_config.contracts[0].address, 'types': 'transaction'}]),
            ]
        )
        self.assertEqual(2, len(client.handlers))

    async def test_on_fetch_operations(self):
        self.datasource._transaction_subscriptions = {self.index_config.contracts[0].address: [OperationType.transaction]}
        with open(join(dirname(__file__), 'operations.json')) as file:
            operations_message = json.load(file)
            del operations_message['state']

        stripped_operations_message = operations_message['data']

        on_operation_message_mock = AsyncMock()
        get_mock = MagicMock()
        get_mock.return_value.__aenter__.return_value.json.return_value = stripped_operations_message

        self.datasource.on_operation_message = on_operation_message_mock

        with patch('aiohttp.ClientSession.get', get_mock):
            await self.datasource.fetch_operations(self.index_config, 9999999)

        on_operation_message_mock.assert_awaited_with(
            message=[operations_message],
            sync=True,
        )

    async def test_on_operations_message_state(self):
        fetch_operations_mock = AsyncMock()
        self.datasource.fetch_operations = fetch_operations_mock

        await self.datasource.on_operation_message([{'type': 0, 'state': 123}], self.index_config)
        fetch_operations_mock.assert_awaited_with(self.index_config, 123)

    async def test_on_operations_message_data(self):
        with open(join(dirname(__file__), 'operations.json')) as file:
            operations_message = json.load(file)
        operation = TzktDatasource.convert_operation(operations_message['data'][-2])

        on_operation_match_mock = AsyncMock()
        self.datasource.on_operation_match = on_operation_match_mock

        async with tortoise_wrapper('sqlite://:memory:'):
            await Tortoise.generate_schemas()

            await self.datasource.on_operation_message([operations_message], sync=True)

            on_operation_match_mock.assert_awaited_with(
                self.index_config,
                self.index_config.handlers[0],
                [operation],
                ANY,
            )

    async def test_on_operation_match(self):
        with open(join(dirname(__file__), 'operations.json')) as file:
            operations_message = json.load(file)
        operations = [TzktDatasource.convert_operation(op) for op in operations_message['data']]
        matched_operation = operations[0]

        async with tortoise_wrapper('sqlite://:memory:'):
            await Tortoise.generate_schemas()

            callback_mock = AsyncMock()
            storage_type_mock = MagicMock()
            storage_type_mock.__fields__ = MagicMock()

            self.index_config.handlers[0].callback_fn = callback_mock
            self.index_config.handlers[0].pattern[0].storage_type_cls = storage_type_mock

            await self.datasource.on_operation_match(self.index_config, self.index_config.handlers[0], [matched_operation], operations)

            self.assertIsInstance(callback_mock.await_args[0][0], HandlerContext)
            self.assertIsInstance(callback_mock.await_args[0][1], Transaction)
            self.assertIsInstance(callback_mock.await_args[0][1].parameter, CollectParameter)
            self.assertIsInstance(callback_mock.await_args[0][1].data, OperationData)

    async def test_on_operation_match_with_storage(self):
        with open(join(dirname(__file__), 'operations-storage.json')) as file:
            operations_message = json.load(file)
        self.index_config.handlers[0].pattern[0].parameter_type_cls = ProposeParameter

        for op in operations_message['data']:
            op['type'] = 'transaction'
        operations = [TzktDatasource.convert_operation(op) for op in operations_message['data']]
        matched_operation = operations[0]

        async with tortoise_wrapper('sqlite://:memory:'):
            await Tortoise.generate_schemas()

            callback_mock = AsyncMock()

            self.index_config.handlers[0].callback_fn = callback_mock
            self.index_config.handlers[0].pattern[0].storage_type_cls = RegistryStorage

            await self.datasource.on_operation_match(self.index_config, self.index_config.handlers[0], [matched_operation], operations)

            self.assertIsInstance(callback_mock.await_args[0][1].storage, RegistryStorage)
            self.assertIsInstance(callback_mock.await_args[0][1].storage.ledger, list)
            self.assertIsInstance(
                callback_mock.await_args[0][1].storage.proposals['e710c1a066bbbf73692168e783607996785260cec4d60930579827298493b8b9'],
                Proposals,
            )

    # async def test_dedup_operations(self) -> None:
    #     operations = [
    #         {'id': 5},
    #         {'id': 3},
    #         {'id': 3},
    #         {'id': 1},
    #     ]
    #     operations = dedup_operations(operations)
    #     self.assertEqual(
    #         [
    #             {'id': 1},
    #             {'id': 3},
    #             {'id': 5},
    #         ],
    #         operations,
    #     )
