# generated by DipDup 7.5.4

from __future__ import annotations

from pydantic import BaseModel
from pydantic import ConfigDict


class Balances(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    approvals: dict[str, str]
    balance: str


class TokenMetadata(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    nat: str
    map: dict[str, str]


class Fa12TokenStorage(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    administrator: str
    balances: dict[str, Balances]
    debtCeiling: str
    governorContractAddress: str
    metadata: dict[str, str]
    paused: bool
    token_metadata: dict[str, TokenMetadata]
    totalSupply: str
