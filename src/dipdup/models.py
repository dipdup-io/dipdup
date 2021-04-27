import logging
from copy import deepcopy
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, get_origin

from pydantic import BaseModel
from pydantic.dataclasses import dataclass
from tortoise import Model, fields
from typing_inspect import get_args  # type: ignore

ParameterType = TypeVar('ParameterType', bound=BaseModel)
StorageType = TypeVar('StorageType', bound=BaseModel)
KeyType = TypeVar('KeyType', bound=BaseModel)
ValueType = TypeVar('ValueType', bound=BaseModel)


_logger = logging.getLogger(__name__)


class IndexType(Enum):
    operation = 'operation'
    big_map = 'big_map'
    block = 'block'
    schema = 'schema'


class State(Model):
    index_name = fields.CharField(256)
    index_type = fields.CharEnumField(IndexType)
    hash = fields.CharField(256)
    level = fields.IntField(default=0)

    class Meta:
        table = 'dipdup_state'


@dataclass
class OperationData:
    # FIXME: Bug in TzKT, shouldn't be optional
    type: Optional[str]
    id: int
    level: int
    timestamp: datetime
    hash: str
    counter: int
    sender_address: str
    target_address: str
    amount: int
    status: str
    has_internals: bool
    storage: Dict[str, Any]
    block: Optional[str] = None
    sender_alias: Optional[str] = None
    nonce: Optional[int] = None
    target_alias: Optional[str] = None
    entrypoint: Optional[str] = None
    parameter_json: Optional[Any] = None
    initiator_address: Optional[str] = None
    parameter: Optional[str] = None
    diffs: Optional[List[Dict[str, Any]]] = None

    def _merge_bigmapdiffs(self, storage_dict: Dict[str, Any], bigmap_name: str, array: bool) -> None:
        if self.diffs is None:
            raise Exception('`bigmaps` field missing')
        _logger.debug(bigmap_name)
        bigmapdiffs = [bm for bm in self.diffs if bm['path'] == bigmap_name]
        bigmap_key = bigmap_name.split('.')[-1]
        for diff in bigmapdiffs:
            _logger.debug('Applying bigmapdiff: %s', diff)
            if diff['action'] in ('add_key', 'update_key'):
                key = diff['content']['key']
                if array is True:
                    storage_dict[bigmap_key].append({'key': key, 'value': diff['content']['value']})
                else:
                    storage_dict[bigmap_key][key] = diff['content']['value']

    def _process_storage(self, storage_type: Type[StorageType], storage: Dict, prefix: str = None):
        for key, field in storage_type.__fields__.items():

            if key == '__root__':
                continue

            if field.alias:
                key = field.alias

            bigmap_name = key if prefix is None else '.'.join([prefix, key])

            # NOTE: TzKT could return bigmaps as object or as array of key-value objects. We need to guess this from storage.
            # TODO: This code should be a part of datasource module.
            if field.type_ not in (int, bool) and isinstance(storage[key], int):
                _logger.debug(field.type_)
                if get_origin(get_args(field.type_)[1]) == list:
                    storage[key] = []
                    if self.diffs:
                        self._merge_bigmapdiffs(storage, bigmap_name, array=True)
                else:
                    storage[key] = {}
                    if self.diffs:
                        self._merge_bigmapdiffs(storage, bigmap_name, array=False)
            elif hasattr(field.type_, '__fields__') and isinstance(storage[key], dict):
                storage[key] = self._process_storage(field.type_, storage[key], bigmap_name)

        return storage

    def get_merged_storage(self, storage_type: Type[StorageType]) -> StorageType:
        if self.storage is None:
            raise Exception('`storage` field missing')

        storage = deepcopy(self.storage)
        _logger.debug('Merging storage')
        _logger.debug('Before: %s', storage)
        _logger.debug('Diffs: %s', self.diffs)

        storage = self._process_storage(storage_type, storage, None)

        _logger.debug('After: %s', storage)

        return storage_type.parse_obj(storage)


@dataclass
class OperationContext(Generic[ParameterType, StorageType]):
    data: OperationData
    parameter: ParameterType
    storage: StorageType


class BigMapAction(Enum):
    ADD = 'add_key'
    UPDATE = 'update_key'
    REMOVE = 'remove_key'


@dataclass
class BigMapContext(Generic[KeyType, ValueType]):
    action: BigMapAction
    key: KeyType
    value: Optional[ValueType]


@dataclass
class BigMapData:
    id: int
    level: int
    # operation_id: int
    timestamp: datetime
    bigmap: int
    contract_address: str
    path: str
    action: str
    key: Optional[str] = None
    value: Optional[str] = None


@dataclass
class OperationHandlerContext:
    operations: List[OperationData]
    template_values: Optional[Dict[str, str]]


@dataclass
class BigMapHandlerContext:
    template_values: Optional[Dict[str, str]]
