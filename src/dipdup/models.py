import logging
from copy import deepcopy
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, get_args, get_origin

from pydantic import BaseModel
from pydantic.dataclasses import dataclass
from tortoise import Model, fields

ParameterType = TypeVar('ParameterType')
StorageType = TypeVar('StorageType', bound=BaseModel)


_logger = logging.getLogger(__name__)


class IndexType(Enum):
    operation = 'operation'
    bigmapdiff = 'bigmapdiff'
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
    # FIXME:
    type: Optional[str]
    id: int
    level: int
    timestamp: datetime
    hash: str
    counter: int
    sender_address: str
    gas_limit: int
    gas_used: int
    storage_limit: int
    storage_used: int
    baker_fee: int
    storage_fee: int
    allocation_fee: int
    target_address: str
    amount: int
    status: str
    has_internals: bool
    block: Optional[str] = None
    sender_alias: Optional[str] = None
    nonce: Optional[int] = None
    target_alias: Optional[str] = None
    entrypoint: Optional[str] = None
    parameter_json: Optional[Any] = None
    initiator_address: Optional[str] = None
    parameter: Optional[str] = None
    storage: Optional[Dict[str, Any]] = None
    bigmaps: Optional[List[Dict[str, Any]]] = None

    def _merge_bigmapdiffs(self, storage_dict: Dict[str, Any], bigmap_name: str) -> None:
        if self.bigmaps is None:
            raise Exception('`bigaps` field missing')
        bigmapdiffs = [bm for bm in self.bigmaps if bm['path'] == bigmap_name]
        for diff in bigmapdiffs:
            if diff['action'] in ('add_key', 'update_key'):
                key = diff['key']['key']
                if isinstance(key, dict):
                    storage_dict[bigmap_name].append({'key': key, 'value': diff['key']['value']})
                elif isinstance(key, str):
                    storage_dict[bigmap_name][key] = diff['key']['value']

    def get_merged_storage(self, storage_type: Type[StorageType]) -> StorageType:
        if self.storage is None:
            raise Exception('`storage` field missing')
        if self.bigmaps is None:
            return storage_type.parse_obj(self.storage)

        storage = deepcopy(self.storage)
        for key, field in storage_type.__fields__.items():
            if field.type_ != int and isinstance(storage[key], int):
                if 'key' in field.type_.__fields__:
                    storage[key] = []
                else:
                    storage[key] = {}

                self._merge_bigmapdiffs(storage, key)

        return storage_type.parse_obj(storage)


@dataclass
class OperationContext(Generic[ParameterType]):
    data: OperationData
    parameter: ParameterType
    storage: Optional[Any] = None


@dataclass
class HandlerContext:
    operations: List[OperationData]
    template_values: Optional[Dict[str, str]]
