from __future__ import annotations

from datetime import datetime
from typing import List
from typing import Union
from unittest import TestCase

from pydantic import BaseModel
from pydantic import Extra

from demo_tezos_domains.types.name_registry.storage import NameRegistryStorage
from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.datasources.tzkt.models import deserialize_storage
from dipdup.models import OperationData
from tests.test_dipdup.models import ResourceCollectorStorage


class SaleToken(BaseModel):
    class Config:
        extra = Extra.forbid

    token_for_sale_address: str
    token_for_sale_token_id: str


class Key(BaseModel):
    class Config:
        extra = Extra.forbid

    sale_seller: str
    sale_token: SaleToken


class BazaarMarketPlaceStorageItem(BaseModel):
    class Config:
        extra = Extra.forbid

    key: Key
    value: str


class BazaarMarketPlaceStorage(BaseModel):
    __root__: Union[int, List[BazaarMarketPlaceStorageItem]]


class BazaarMarketPlaceStorageTest(BaseModel):
    __root__: BazaarMarketPlaceStorage


class ModelsTest(TestCase):
    def test_merged_storage(self) -> None:
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
        operation_data = OperationData(
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
        merged_storage = deserialize_storage(operation_data, NameRegistryStorage)
        self.assertTrue('6672657175656e742d616e616c7973742e65646f' in merged_storage.store.records)

    def test_merged_storage_dict_of_dicts(self) -> None:
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
        operation_data = OperationData(
            storage=storage,
            diffs=None,
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
        deserialize_storage(operation_data, ResourceCollectorStorage)

    def test_merged_storage_plain_list(self) -> None:
        operation_data_json = {
            "type": "transaction",
            "id": 43285851,
            "level": 1388947,
            "timestamp": "2021-03-17T17:57:33Z",
            "block": "BLWWxXoqEjZHsVZfKSh17TCvVa2ReJ6EMKNmpUbwsWJHNRSnC9J",
            "hash": "opZ4CeGANGUW19i1HgxGh32qHaqL9FUg8GyqjYPcrgLjgBXbvDF",
            "counter": 11744585,
            "sender": {"address": "tz1QX6eLPYbRcakYbiUy7i8krXEgc5XL3Lhb"},
            "gasLimit": 47114,
            "gasUsed": 25646,
            "storageLimit": 69,
            "storageUsed": 69,
            "bakerFee": 5061,
            "storageFee": 17250,
            "allocationFee": 0,
            "target": {"address": "KT1E8Qzgx3C5AAE4iGuXvqSQjdd21LK2aXAk"},
            "amount": 0,
            "parameter": {
                "entrypoint": "sell",
                "value": {
                    "sale_price": "1000000",
                    "sale_token_param_tez": {
                        "token_for_sale_address": "KT1X6Z5dxjhmy7eMZPwCMrf5EagG9MgSS8G2",
                        "token_for_sale_token_id": "0",
                    },
                },
            },
            "storage": 750,
            "diffs": [
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
            ],
            "status": "applied",
            "hasInternals": True,
            "parameters": "{\"entrypoint\":\"sell\",\"value\":{\"prim\":\"Pair\",\"args\":[{\"int\":\"1000000\"},{\"prim\":\"Pair\",\"args\":[{\"string\":\"KT1X6Z5dxjhmy7eMZPwCMrf5EagG9MgSS8G2\"},{\"int\":\"0\"}]}]}}",
        }

        operation_data = TzktDatasource.convert_operation(operation_data_json)
        storage = deserialize_storage(operation_data, BazaarMarketPlaceStorage)
        self.assertEqual('tz1QX6eLPYbRcakYbiUy7i8krXEgc5XL3Lhb', storage.__root__[0].key.sale_seller)  # type: ignore
