# generated by datamodel-codegen:
#   filename:  storage.json

from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from pydantic import Extra


class Key(BaseModel):
    class Config:
        extra = Extra.forbid

    address_0: str
    address_1: str
    nat: str


class Operator(BaseModel):
    class Config:
        extra = Extra.forbid

    key: Key
    value: dict[str, Any]


class TokenMetadata(BaseModel):
    class Config:
        extra = Extra.forbid

    token_id: str
    token_info: dict[str, str]


class Assets(BaseModel):
    class Config:
        extra = Extra.forbid

    ledger: dict[str, str]
    next_token_id: str
    operators: list[Operator]
    token_metadata: dict[str, TokenMetadata]


class FtzFunStorage(BaseModel):
    class Config:
        extra = Extra.forbid

    assets: Assets
    metadata: dict[str, str]