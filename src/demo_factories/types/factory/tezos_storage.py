# generated by DipDup 7.5.4

from __future__ import annotations

from pydantic import BaseModel
from pydantic import ConfigDict


class Ledger(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    allowances: list[str]
    balance: str
    frozen_balance: str


class TokenList(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    address: str
    nat: str


class Key(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    address: str
    nat: str


class TokenToExchangeItem(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    key: Key
    value: str


class UserRewards(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    reward: str
    reward_paid: str


class Voters(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    candidate: str | None = None
    last_veto: str
    veto: str
    vote: str


class FactoryStorage(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    baker_validator: str
    counter: str
    dex_lambdas: dict[str, str]
    ledger: dict[str, Ledger]
    metadata: dict[str, str]
    token_lambdas: dict[str, str]
    token_list: dict[str, TokenList]
    token_to_exchange: list[TokenToExchangeItem]
    user_rewards: dict[str, UserRewards]
    vetos: dict[str, str]
    voters: dict[str, Voters]
    votes: dict[str, str]
