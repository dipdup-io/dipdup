from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import orjson as json

from dipdup.indexes.tezos_tzkt_operations.parser import deserialize_storage
from dipdup.models.tezos_tzkt import TzktOperationData
from tests.types.asdf.storage import AsdfStorage
from tests.types.bazaar.storage import BazaarMarketPlaceStorage
from tests.types.ftzfun.storage import FtzFunStorage
from tests.types.hen_subjkt.storage import HenSubjktStorage
from tests.types.hjkl.storage import HjklStorage
from tests.types.kolibri_ovens.set_delegate import SetDelegateParameter
from tests.types.kolibri_ovens.storage import KolibriOvensStorage
from tests.types.listofmaps.storage import ListOfMapsStorage
from tests.types.qwer.storage import QwerStorage
from tests.types.rewq.storage import RewqStorage
from tests.types.tezotop.storage import ResourceCollectorStorage
from tests.types.yupana.storage import YupanaStorage
from tests.types.zxcv.storage import ZxcvStorage


def get_operation_data(storage: Any, diffs: tuple[dict[str, Any], ...]) -> TzktOperationData:
    return TzktOperationData(
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


def test_deserialize_storage_nested_dicts() -> None:
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
    operation_data = get_operation_data(storage, ())

    # Arc
    _, storage_obj = deserialize_storage(operation_data, ResourceCollectorStorage)

    # Assert
    assert isinstance(storage_obj, ResourceCollectorStorage)
    assert isinstance(storage_obj.metadata, dict)
    assert isinstance(storage_obj.tezotop_collection, dict)


def test_deserialize_storage_plain_list() -> None:
    # Arrange
    storage = 750
    diffs = (
        {
            'bigmap': 750,
            'path': '',
            'action': 'add_key',
            'content': {
                'hash': 'exprtkgkbpybdsS74tPVswD6MjtdMZksCF8NQjSPScrq1Qk1m9mGzR',
                'key': {
                    'sale_token': {
                        'token_for_sale_address': 'KT1X6Z5dxjhmy7eMZPwCMrf5EagG9MgSS8G2',
                        'token_for_sale_token_id': '0',
                    },
                    'sale_seller': 'tz1QX6eLPYbRcakYbiUy7i8krXEgc5XL3Lhb',
                },
                'value': '1000000',
            },
        },
    )
    operation_data = get_operation_data(storage, diffs)

    # Act
    _, storage_obj = deserialize_storage(operation_data, BazaarMarketPlaceStorage)

    # Assert
    assert isinstance(storage_obj, BazaarMarketPlaceStorage)
    assert isinstance(storage_obj.__root__, list)
    assert storage_obj.__root__[0].key.sale_seller == 'tz1QX6eLPYbRcakYbiUy7i8krXEgc5XL3Lhb'


def test_deserialize_storage_list_of_maps() -> None:
    # Arrange
    storage = [164576, 164577, 164578]
    diffs = (
        {'bigmap': 164578, 'path': '2', 'action': 'allocate'},
        {
            'bigmap': 164578,
            'path': '2',
            'action': 'add_key',
            'content': {
                'hash': 'exprtsjEVVZk3Gm82U9wEs8kvwRiQwUT7zipJwvCeFMNsApe2tQ15s',
                'key': 'hello',
                'value': '42',
            },
        },
        {
            'bigmap': 164578,
            'path': '2',
            'action': 'add_key',
            'content': {
                'hash': 'exprv9qnaSha415Hm49U3YxG2Q3EAyhabvky3avPRGG8AX9Nk69SbN',
                'key': 'hi',
                'value': '100500',
            },
        },
        {'bigmap': 164577, 'path': '1', 'action': 'allocate'},
        {
            'bigmap': 164577,
            'path': '1',
            'action': 'add_key',
            'content': {
                'hash': 'exprvNX6heZJnVkgZf8Xvq9DKEJE3mazxE69KxVSFxGi2RYQqNpKWz',
                'key': 'test',
                'value': '123',
            },
        },
        {'bigmap': 164576, 'path': '0', 'action': 'allocate'},
    )
    operation_data = get_operation_data(storage, diffs)

    # Act
    _, storage_obj = deserialize_storage(operation_data, ListOfMapsStorage)

    # Assert
    assert isinstance(storage_obj, ListOfMapsStorage)
    assert isinstance(storage_obj.__root__, list)
    assert storage_obj.__root__[1]['test'] == '123'


def test_convert_operation_with_default_entrypoint() -> None:
    # Arrange
    json_path = Path(__file__).parent / 'responses' / 'ooQuCAKBHkmWy2VciDAV9c6CFTywuMLupLzVoKDwS1xvR4EdRng.json'
    operations_json = json.loads(json_path.read_bytes())

    # Act
    operations = [TzktOperationData.from_json(op) for op in operations_json]

    # Assert
    assert operations[0].entrypoint == 'default'
    assert operations[0].parameter_json == {}
    assert operations[1].entrypoint == 'deposit'
    assert operations[1].parameter_json != {}


def test_deserialize_storage_dict_key() -> None:
    # Arrange
    json_path = Path(__file__).parent / 'responses' / 'ftzfun.json'
    operations_json = json.loads(json_path.read_bytes())

    # Act
    operations = [TzktOperationData.from_json(op) for op in operations_json]
    _, storage_obj = deserialize_storage(operations[0], FtzFunStorage)

    # Assert
    assert isinstance(storage_obj, FtzFunStorage)
    assert isinstance(storage_obj.assets.operators, list)
    assert storage_obj.assets.operators[0].key.address_0 == 'tz1fMia93yL7vndY2fZ5rGAQPgex7RQHXV1m'
    assert storage_obj.assets.operators[0].value == {}


def test_qwer() -> None:
    json_path = Path(__file__).parent / 'responses' / 'qwer.json'
    operations_json = json.loads(json_path.read_bytes())

    # Act
    operations = [TzktOperationData.from_json(op) for op in operations_json]
    _, storage_obj = deserialize_storage(operations[0], QwerStorage)

    # Assert
    assert isinstance(storage_obj, QwerStorage)
    assert isinstance(storage_obj.__root__, list)
    assert storage_obj.__root__[0][1].R['1'] == '1'  # type: ignore[union-attr]
    assert storage_obj.__root__[0][1].R['2'] == '2'  # type: ignore[union-attr]


def test_asdf() -> None:
    json_path = Path(__file__).parent / 'responses' / 'asdf.json'
    operations_json = json.loads(json_path.read_bytes())

    # Act
    operations = [TzktOperationData.from_json(op) for op in operations_json]
    _, storage_obj = deserialize_storage(operations[0], AsdfStorage)

    # Assert
    assert isinstance(storage_obj, AsdfStorage)
    assert isinstance(storage_obj.__root__, list)
    assert isinstance(storage_obj.__root__[0]['pupa'], list)


def test_hjkl() -> None:
    json_path = Path(__file__).parent / 'responses' / 'hjkl.json'
    operations_json = json.loads(json_path.read_bytes())

    # Act
    operations = [TzktOperationData.from_json(op) for op in operations_json]
    _, storage_obj = deserialize_storage(operations[0], HjklStorage)

    # Assert
    assert isinstance(storage_obj, HjklStorage)
    assert isinstance(storage_obj.__root__, list)
    assert isinstance(storage_obj.__root__[0].value.mr, dict)
    assert storage_obj.__root__[0].value.mr['111'] is True


def test_zxcv() -> None:
    json_path = Path(__file__).parent / 'responses' / 'zxcv.json'
    operations_json = json.loads(json_path.read_bytes())

    # Act
    operations = [TzktOperationData.from_json(op) for op in operations_json]
    _, storage_obj = deserialize_storage(operations[0], ZxcvStorage)

    # Assert
    assert isinstance(storage_obj, ZxcvStorage)
    assert isinstance(storage_obj.big_map, dict)
    assert storage_obj.big_map['111'].L == '222'  # type: ignore[union-attr]
    assert storage_obj.map['happy'].R == 'new year'  # type: ignore[union-attr]
    assert storage_obj.map['merry'].L == 'christmas'  # type: ignore[union-attr]
    assert storage_obj.or_.R == '42'  # type: ignore[union-attr]
    assert storage_obj.unit == {}


def test_rewq() -> None:
    json_path = Path(__file__).parent / 'responses' / 'rewq.json'
    operations_json = json.loads(json_path.read_bytes())

    # Act
    operations = [TzktOperationData.from_json(op) for op in operations_json]
    _, storage_obj = deserialize_storage(operations[0], RewqStorage)

    # Assert
    assert isinstance(storage_obj, RewqStorage)
    assert isinstance(storage_obj.map, dict)
    assert isinstance(storage_obj.map['try'].L, dict)  # type: ignore[union-attr]
    assert storage_obj.map['try'].L['111'] == '222'  # type: ignore[union-attr]
    assert isinstance(storage_obj.or_.L, dict)  # type: ignore[union-attr]
    assert storage_obj.or_.L['333'] == '444'  # type: ignore[union-attr]


def test_hen_subjkt() -> None:
    json_path = Path(__file__).parent / 'responses' / 'hen_subjkt.json'
    operations_json = json.loads(json_path.read_bytes())

    # Act
    operations = [TzktOperationData.from_json(op) for op in operations_json]
    _, storage_obj = deserialize_storage(operations[0], HenSubjktStorage)

    # Assert
    assert isinstance(storage_obj, HenSubjktStorage)
    assert isinstance(storage_obj.entries, dict)
    assert storage_obj.entries['tz1Y1j7FK1X9Rrv2VdPz5bXoU7SszF8W1RnK'] is True


def test_kolibri_ovens() -> None:
    json_path = Path(__file__).parent / 'responses' / 'kolibri_ovens.json'
    operations_json = json.loads(json_path.read_bytes())

    # Act
    operations = [TzktOperationData.from_json(op) for op in operations_json]
    _, storage_obj = deserialize_storage(operations[0], KolibriOvensStorage)
    parameter_obj = SetDelegateParameter.parse_obj(operations[0].parameter_json)

    # Assert
    assert isinstance(storage_obj, KolibriOvensStorage)
    assert isinstance(parameter_obj, SetDelegateParameter)
    assert parameter_obj.__root__ is None


def test_yupana() -> None:
    json_path = Path(__file__).parent / 'responses' / 'yupana.json'
    operations_json = json.loads(json_path.read_bytes())

    # Act
    operations = [TzktOperationData.from_json(op) for op in operations_json]
    _, storage_obj = deserialize_storage(operations[0], YupanaStorage)

    # Assert
    assert isinstance(storage_obj, YupanaStorage)
    assert isinstance(storage_obj.storage.markets, dict)
    assert storage_obj.storage.markets['tz1MDhGTfMQjtMYFXeasKzRWzkQKPtXEkSEw'] == ['0']


def _load_response(name: str) -> Any:
    path = Path(__file__).parent / 'responses' / name
    return json.loads(path.read_bytes())


def test_origination_amount() -> None:
    operations_json = _load_response('origination_amount.json')
    operation = TzktOperationData.from_json(operations_json[0])

    assert operation.amount == 31000000
