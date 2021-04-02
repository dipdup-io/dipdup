from datetime import datetime
from symbol import parameters
from typing import Any, Generic, Optional, TypeVar

from attr import dataclass
from tortoise import Model, fields

ParameterType = TypeVar('ParameterType')


class State(Model):
    dapp = fields.CharField(128)
    level = fields.IntField(default=0)


class Transaction(Model):
    id = fields.IntField(pk=True)
    block = fields.CharField(58)


@dataclass(kw_only=True)
class OperationData:
    type: str
    id: int
    level: int
    timestamp: datetime
    block: str
    hash: str
    counter: int
    initiator_address: Optional[str] = None
    sender_address: str
    sender_alias: Optional[str] = None
    nonce: Optional[int] = None
    gas_limit: int
    gas_used: int
    storage_limit: int
    storage_used: int
    baker_fee: int
    storage_fee: int
    allocation_fee: int
    target_alias: Optional[str] = None
    target_address: str
    amount: int
    entrypoint: Optional[str] = None
    parameter_json: Optional[Any] = None
    status: str
    has_internals: bool
    parameter: Optional[str] = None


@dataclass(kw_only=True)
class HandlerContext(Generic[ParameterType]):
    data: OperationData
    transaction: Transaction
    parameter: ParameterType
