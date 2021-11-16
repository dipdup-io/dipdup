from typing import Literal

from pydantic.dataclasses import dataclass

from dipdup.const import OperationType


@dataclass
class OperationParameters:
    dst: str
    entrypoint: str


@dataclass
class OperationFields:
    # from tzkt api
    ...


@dataclass
class OperationFeeData:
    gas_limit: int
    storage_limit: int
    storage_fee: int


@dataclass
class TransactionOperationDTO(OperationParameters, OperationFields, OperationFeeData):
    type: Literal[OperationType.transaction]
    # whole set of fields
    ...
