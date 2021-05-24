# generated by datamodel-codegen:
#   filename:  storage.json

from __future__ import annotations

from typing import Dict

from pydantic import BaseModel


class Balances(BaseModel):
    approvals: Dict[str, str]
    balance: str


class TokenMetadata(BaseModel):
    int: str
    map: Dict[str, str]


class TokenSWAPStorage(BaseModel):
    administrator: str
    balances: Dict[str, Balances]
    metadata: Dict[str, str]
    paused: bool
    token_metadata: Dict[str, TokenMetadata]
    totalSupply: str
