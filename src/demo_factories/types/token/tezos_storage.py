# generated by DipDup 7.5.4

from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict


class Key(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    address: str
    nat: str


class LedgerItem(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    key: Key
    value: str


class Key1(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    owner: str
    operator: str
    token_id: str


class Operator(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    key: Key1
    value: dict[str, Any]


class TokenMetadata(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    token_id: str
    token_info: dict[str, str]


class TokenStorage(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    administrator: str
    all_tokens: str
    isMinter1Locked: bool
    isMinter2Locked: bool
    ledger: list[LedgerItem]
    metadata: dict[str, str]
    minter1: str
    minter2: str
    operators: list[Operator]
    paused: bool
    token_metadata: dict[str, TokenMetadata]
