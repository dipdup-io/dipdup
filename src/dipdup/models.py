from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic.dataclasses import dataclass
from tortoise import Model, fields

ParameterType = TypeVar('ParameterType')


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
    type: str
    id: int
    level: int
    timestamp: datetime
    block: str
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
    sender_alias: Optional[str] = None
    nonce: Optional[int] = None
    target_alias: Optional[str] = None
    entrypoint: Optional[str] = None
    parameter_json: Optional[Any] = None
    initiator_address: Optional[str] = None
    parameter: Optional[str] = None


@dataclass
class OperationContext(Generic[ParameterType]):
    data: OperationData
    parameter: ParameterType


@dataclass
class HandlerContext:
    operations: List[OperationData]
    template_values: Optional[Dict[str, str]]
