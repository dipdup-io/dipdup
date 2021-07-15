from unittest import TestCase

from demo_tezos_domains.types.name_registry.storage import NameRegistryStorage
from dipdup.models import OperationData


class ModelsTest(TestCase):
    def test_merged_storage(self):
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
            timestamp=0,
            hash='',
            counter=0,
            sender_address='',
            target_address='',
            initiator_address='',
            amount=0,
            status='',
            has_internals=False,
        )
        merged_storage = operation_data.get_merged_storage(NameRegistryStorage)
        self.assertTrue('6672657175656e742d616e616c7973742e65646f' in merged_storage.store.records)
