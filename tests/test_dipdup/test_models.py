from __future__ import annotations

from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from unittest import TestCase

from demo_tezos_domains.types.name_registry.storage import NameRegistryStorage
from dipdup.datasources.tzkt.models import deserialize_storage
from dipdup.models import OperationData
from tests.test_dipdup.models import ResourceCollectorStorage
from tests.test_dipdup.types import BazaarMarketPlaceStorage
from tests.test_dipdup.types import ListOfMapsStorage


def get_operation_data(storage: Any, diffs: List[Dict[str, Any]]) -> OperationData:
    return OperationData(
        storage=storage,
        diffs=diffs,
        type='transaction',
        id=0,
        level=0,
        timestamp=datetime.now(),
        hash='',
        counter=0,
        sender_address='',
        target_address='',
        initiator_address='',
        amount=0,
        status='',
        has_internals=False,
    )


class ModelsTest(TestCase):
    def test_deserialize_storage_dict(self) -> None:
        # Arrange
        storage = {
            'store': {
                'data': 15023,
                'owner': 'tz1VBLpuDKMoJuHRLZ4HrCgRuiLpEr7zZx2E',
                'records': 15026,
                'metadata': 15025,
                'expiry_map': 15024,
                'tzip12_tokens': 15028,
                'reverse_records': 15027,
                'next_tzip12_token_id': '18',
            },
            'actions': 15022,
            'trusted_senders': [
                'KT19fHFeGecCBRePPMoRjMthJ9YZCJkB5MsN',
                'KT1A84aNsVCG7EsZyKHSyqZacVVSN1zcQzS7',
                'KT1AQmVzLnNWtCmksbCGg7np9dmAU5CKYH72',
                'KT1EeRLdEPJPFx96tDM1VgRka2V6ZyKV4vRg',
                'KT1FpHyP8vUd7p2aq7DLRccUVPixoGVB4fJE',
                'KT1HKtJxcr8dMTJMUiiFhttA6rk4v6xqTkmH',
                'KT1KP2Yy6MNkYKkHqroGBZ7KFN5NdNfnUHHv',
                'KT1LE3iTYfJNWkmPoa3KzN45y1QFKF6GA42Q',
                'KT1Mq1zd986PxK4C2y9S7UaJkhTBbY15AU32',
            ],
        }
        diffs = [
            {
                'bigmap': 15028,
                'path': 'store.tzip12_tokens',
                'action': 'add_key',
                'content': {
                    'hash': 'expruh5diuJb6Vu4B127cxWhiJ3927mvmG9oZ1pYKSNERPpefM4KBg',
                    'key': '17',
                    'value': '6672657175656e742d616e616c7973742e65646f',
                },
            },
            {
                'bigmap': 15026,
                'path': 'store.records',
                'action': 'add_key',
                'content': {
                    'hash': 'expruDKynBfQW5KFzPfKyRxNTfFzTJGrHUU4FpzBZcoRYXjyhdPPrM',
                    'key': '6672657175656e742d616e616c7973742e65646f',
                    'value': {
                        'data': {},
                        'level': '2',
                        'owner': 'tz1SUrXU6cxioeyURSxTgaxmpSWgQq4PMSov',
                        'address': 'tz1SUrXU6cxioeyURSxTgaxmpSWgQq4PMSov',
                        'expiry_key': '6672657175656e742d616e616c7973742e65646f',
                        'internal_data': {},
                        'tzip12_token_id': '17',
                    },
                },
            },
            {
                'bigmap': 15024,
                'path': 'store.expiry_map',
                'action': 'add_key',
                'content': {
                    'hash': 'expruDKynBfQW5KFzPfKyRxNTfFzTJGrHUU4FpzBZcoRYXjyhdPPrM',
                    'key': '6672657175656e742d616e616c7973742e65646f',
                    'value': '2024-02-29T15:45:49Z',
                },
            },
        ]
        operation_data = get_operation_data(storage, diffs)

        # Act
        storage_obj = deserialize_storage(operation_data, NameRegistryStorage)

        # Assert
        self.assertIsInstance(storage_obj, NameRegistryStorage)
        self.assertIsInstance(storage_obj.store.records, dict)
        self.assertIn('6672657175656e742d616e616c7973742e65646f', storage_obj.store.records)

    def test_deserialize_storage_nested_dicts(self) -> None:
        # Arrange
        storage = {
            'paused': False,
            'managers': ['tz1VPZyh4ZHjDDpgvznqQQXUCLcV7g91WGMz'],
            'metadata': 43542,
            'current_user': 'tz1VPZyh4ZHjDDpgvznqQQXUCLcV7g91WGMz',
            'nft_registry': 'KT1SZ87ihAWc43YZxYjoRz8MQyAapUGbZigG',
            'resource_map': {
                'enr': {'id': '2', 'rate': '1875000'},
                'mch': {'id': '3', 'rate': '625000'},
                'min': {'id': '1', 'rate': '1250000'},
                'uno': {'id': '0', 'rate': '1250'},
            },
            'administrator': 'tz1VPZyh4ZHjDDpgvznqQQXUCLcV7g91WGMz',
            'generation_rate': '9',
            'resource_registry': 'KT1SLaZNaDF7V6Lt8FXTbYNqkBS81gjHXMsP',
            'default_start_time': '1630678200',
            'tezotop_collection': 43543,
        }
        operation_data = get_operation_data(storage, [])

        # Arc
        storage_obj = deserialize_storage(operation_data, ResourceCollectorStorage)

        # Assert
        self.assertIsInstance(storage_obj, ResourceCollectorStorage)
        self.assertIsInstance(storage_obj.metadata, dict)
        self.assertIsInstance(storage_obj.tezotop_collection, dict)

    def test_deserialize_storage_plain_list(self) -> None:
        # Arrange
        storage = 750
        diffs = [
            {
                "bigmap": 750,
                "path": "",
                "action": "add_key",
                "content": {
                    "hash": "exprtkgkbpybdsS74tPVswD6MjtdMZksCF8NQjSPScrq1Qk1m9mGzR",
                    "key": {
                        "sale_token": {
                            "token_for_sale_address": "KT1X6Z5dxjhmy7eMZPwCMrf5EagG9MgSS8G2",
                            "token_for_sale_token_id": "0",
                        },
                        "sale_seller": "tz1QX6eLPYbRcakYbiUy7i8krXEgc5XL3Lhb",
                    },
                    "value": "1000000",
                },
            }
        ]
        operation_data = get_operation_data(storage, diffs)

        # Act
        storage_obj = deserialize_storage(operation_data, BazaarMarketPlaceStorage)

        # Assert
        self.assertIsInstance(storage_obj, BazaarMarketPlaceStorage)
        self.assertIsInstance(storage_obj.__root__, list)
        self.assertEqual('tz1QX6eLPYbRcakYbiUy7i8krXEgc5XL3Lhb', storage_obj.__root__[0].key.sale_seller)  # type: ignore

    def test_deserialize_storage_list_of_maps(self) -> None:
        # Arrange
        storage = [164576, 164577, 164578]
        diffs = [
            {"bigmap": 164578, "path": "2", "action": "allocate"},
            {
                "bigmap": 164578,
                "path": "2",
                "action": "add_key",
                "content": {"hash": "exprtsjEVVZk3Gm82U9wEs8kvwRiQwUT7zipJwvCeFMNsApe2tQ15s", "key": "hello", "value": "42"},
            },
            {
                "bigmap": 164578,
                "path": "2",
                "action": "add_key",
                "content": {"hash": "exprv9qnaSha415Hm49U3YxG2Q3EAyhabvky3avPRGG8AX9Nk69SbN", "key": "hi", "value": "100500"},
            },
            {"bigmap": 164577, "path": "1", "action": "allocate"},
            {
                "bigmap": 164577,
                "path": "1",
                "action": "add_key",
                "content": {"hash": "exprvNX6heZJnVkgZf8Xvq9DKEJE3mazxE69KxVSFxGi2RYQqNpKWz", "key": "test", "value": "123"},
            },
            {"bigmap": 164576, "path": "0", "action": "allocate"},
        ]
        operation_data = get_operation_data(storage, diffs)

        # Act
        storage_obj = deserialize_storage(operation_data, ListOfMapsStorage)

        # Assert
        self.assertIsInstance(storage_obj, ListOfMapsStorage)
        self.assertIsInstance(storage_obj.__root__, list)
        self.assertEqual(storage_obj.__root__[1]['test'], '123')
