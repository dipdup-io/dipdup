import json
from os.path import dirname, join
from typing import Any, Dict, List, Optional, Union
from unittest import IsolatedAsyncioTestCase
from unittest.mock import ANY, AsyncMock, MagicMock, call, patch

from aiosignalrcore.hub.base_hub_connection import BaseHubConnection  # type: ignore
from aiosignalrcore.transport.websockets.connection import ConnectionState  # type: ignore
from pydantic import BaseModel, Extra
from tortoise import Tortoise

from dipdup.config import ContractConfig, OperationHandlerConfig, OperationHandlerPatternConfig, OperationIndexConfig
from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.models import HandlerContext, IndexType, OperationContext, OperationData, State
from dipdup.utils import tortoise_wrapper


class Key(BaseModel):
    address: str
    nat: str


class LedgerItem(BaseModel):
    key: Key
    value: str


class Key1(BaseModel):
    owner: str
    operator: str


class Operator(BaseModel):
    key: Key1
    value: Dict[str, Any]


class MigrationStatu(BaseModel):
    notInMigration: Dict[str, Any]


class MigrationStatu1(BaseModel):
    migratingTo: str


class MigrationStatu2(BaseModel):
    migratedTo: str


class RegistryItem(BaseModel):
    pass

    class Config:
        extra = Extra.allow


class ExtraModel(BaseModel):
    registry: Union[int, RegistryItem]
    proposal_receivers: List[str]
    frozen_scale_value: str
    frozen_extra_value: str
    slash_scale_value: str
    slash_division_value: str
    max_proposal_size: str


class DiffItem(BaseModel):
    key: str
    new_value: Optional[str]


class ProposalType0(BaseModel):
    agora_post_id: str
    diff: List[DiffItem]


class Metadatum(BaseModel):
    proposal_type_0: ProposalType0


class ProposalType1(BaseModel):
    frozen_scale_value: Optional[str]
    frozen_extra_value: Optional[str]
    slash_scale_value: Optional[str]
    slash_division_value: Optional[str]
    max_proposal_size: Optional[str]


class Metadatum1(BaseModel):
    proposal_type_1: ProposalType1


class Metadatum2(BaseModel):
    receivers_0: List[str]


class Metadatum3(BaseModel):
    receivers_1: List[str]


class Voter(BaseModel):
    address: str
    nat: str


class Proposals(BaseModel):
    class Config:
        extra = Extra.allow

    upvotes: str
    downvotes: str
    start_date: str
    metadata: Union[Metadatum, Metadatum1, Metadatum2, Metadatum3]
    proposer: str
    proposer_frozen_token: str
    voters: List[Voter]


class ProposalKeyListSortByDateItem(BaseModel):
    timestamp: str
    bytes: str


class Metadata(BaseModel):
    class Config:
        extra = Extra.allow

    __root__: str


class TotalSupply(BaseModel):
    class Config:
        extra = Extra.allow

    __root__: str


class Storage(BaseModel):
    ledger: List[LedgerItem]
    operators: List[Operator]
    token_address: str
    admin: str
    pending_owner: str
    migration_status: Union[MigrationStatu, MigrationStatu1, MigrationStatu2]
    voting_period: str
    quorum_threshold: str
    extra: ExtraModel
    proposals: Dict[str, Proposals]
    proposal_key_list_sort_by_date: List[ProposalKeyListSortByDateItem]
    permits_counter: str
    metadata: Dict[str, Metadata]
    total_supply: Dict[str, TotalSupply]


class ProposalMetadatum(BaseModel):
    proposal_type_0: ProposalType0


class ProposalMetadatum1(BaseModel):
    proposal_type_1: ProposalType1


class ProposalMetadatum2(BaseModel):
    receivers_0: List[str]


class ProposalMetadatum3(BaseModel):
    receivers_1: List[str]


class Propose(BaseModel):
    frozen_token: str
    proposal_metadata: Union[ProposalMetadatum, ProposalMetadatum1, ProposalMetadatum2, ProposalMetadatum3]


class Collect(BaseModel):
    objkt_amount: str
    swap_id: str


class TzktDatasourceTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.index_config = OperationIndexConfig(
            kind='operation',
            datasource='tzkt',
            contract=ContractConfig(address='KT1Hkg5qeNhfwpKW4fXvq7HGZB9z2EnmCCA9'),
            handlers=[
                OperationHandlerConfig(
                    callback='',
                    pattern=[
                        OperationHandlerPatternConfig(
                            destination=ContractConfig(address='KT1Hkg5qeNhfwpKW4fXvq7HGZB9z2EnmCCA9'), entrypoint='collect'
                        )
                    ],
                )
            ],
        )
        self.index_config.state = State(index_name='test', index_type=IndexType.operation, hash='')
        self.index_config.handlers[0].pattern[0].parameter_type_cls = Collect
        self.datasource = TzktDatasource('tzkt.test')
        self.datasource.add_index(self.index_config)

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
        get_mock.return_value.__aenter__.return_value.json.return_value = [{'level': 1337}]

        with patch('aiohttp.ClientSession.get', get_mock):
            await self.datasource.start()

        fetch_operations_mock.assert_awaited_with(1337, initial=True)
        self.assertEqual({self.index_config.contract: ['transaction']}, self.datasource._subscriptions)
        client.start.assert_awaited()

    async def test_on_connect_subscribe_to_operations(self):
        send_mock = AsyncMock()
        client = self.datasource._get_client()
        client.send = send_mock
        client.transport.state = ConnectionState.connected
        self.datasource._subscriptions = {
            self.index_config.contract: ['transaction'],
        }

        await self.datasource.on_connect()

        send_mock.assert_has_awaits(
            [
                call('SubscribeToOperations', [{'address': self.index_config.contract.address, 'types': 'transaction'}]),
            ]
        )
        self.assertEqual(1, len(client.handlers))

    async def test_on_fetch_operations(self):
        self.datasource._subscriptions = {self.index_config.contract.address: ['transaction']}
        with open(join(dirname(__file__), 'operations.json')) as file:
            operations_message = json.load(file)
            del operations_message['state']
        stripped_operations_message = operations_message['data']

        on_operation_message_mock = AsyncMock()
        get_mock = MagicMock()
        get_mock.return_value.__aenter__.return_value.json.return_value = stripped_operations_message

        self.datasource.on_operation_message = on_operation_message_mock

        with patch('aiohttp.ClientSession.get', get_mock):
            await self.datasource.fetch_operations(1337)

        on_operation_message_mock.assert_awaited_with(
            address=self.index_config.contract.address,
            message=[operations_message],
            sync=True,
        )

    async def test_on_operation_message_state(self):
        fetch_operations_mock = AsyncMock()
        self.datasource.fetch_operations = fetch_operations_mock

        await self.datasource.on_operation_message([{'type': 0, 'state': 123}], self.index_config.contract.address)
        fetch_operations_mock.assert_awaited_with(123)

    async def test_on_operation_message_data(self):
        with open(join(dirname(__file__), 'operations.json')) as file:
            operations_message = json.load(file)
        operations = [TzktDatasource.convert_operation(op) for op in operations_message['data']]
        operation = TzktDatasource.convert_operation(operations_message['data'][-2])

        on_operation_match_mock = AsyncMock()
        self.datasource.on_operation_match = on_operation_match_mock

        async with tortoise_wrapper('sqlite://:memory:'):
            await Tortoise.generate_schemas()

            await self.datasource.on_operation_message([operations_message], self.index_config.contract.address, sync=True)

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

            self.datasource._synchronized.set()
            await self.datasource.on_operation_match(self.index_config, self.index_config.handlers[0], [matched_operation], operations)

            self.assertIsInstance(callback_mock.await_args[0][0], HandlerContext)
            self.assertIsInstance(callback_mock.await_args[0][1], OperationContext)
            self.assertIsInstance(callback_mock.await_args[0][1].parameter, Collect)
            self.assertIsInstance(callback_mock.await_args[0][1].data, OperationData)

    async def test_on_operation_match_with_storage(self):
        with open(join(dirname(__file__), 'operations-storage.json')) as file:
            operations_message = json.load(file)
        self.index_config.handlers[0].pattern[0].parameter_type_cls = Propose

        operations = [TzktDatasource.convert_operation(op) for op in operations_message['data']]
        matched_operation = operations[0]

        async with tortoise_wrapper('sqlite://:memory:'):
            await Tortoise.generate_schemas()

            callback_mock = AsyncMock()

            self.index_config.handlers[0].callback_fn = callback_mock
            self.index_config.handlers[0].pattern[0].storage_type_cls = Storage

            self.datasource._synchronized.set()
            await self.datasource.on_operation_match(self.index_config, self.index_config.handlers[0], [matched_operation], operations)

            self.assertIsInstance(callback_mock.await_args[0][1].storage, Storage)
            self.assertIsInstance(callback_mock.await_args[0][1].storage.ledger, list)
            self.assertIsInstance(
                callback_mock.await_args[0][1].storage.proposals['e710c1a066bbbf73692168e783607996785260cec4d60930579827298493b8b9'],
                Proposals,
            )
