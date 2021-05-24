# generated by datamodel-codegen:
#   filename:  storage.json

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel


class Ledger(BaseModel):
    allowances: List[str]
    balance: str
    frozen_balance: str


class UserRewards(BaseModel):
    reward: str
    reward_paid: str


class Voters(BaseModel):
    candidate: Optional[str]
    last_veto: str
    veto: str
    vote: str


class Storage(BaseModel):
    baker_validator: str
    current_candidate: Optional[str]
    current_delegated: Optional[str]
    last_update_time: str
    last_veto: str
    ledger: Dict[str, Ledger]
    period_finish: str
    reward: str
    reward_paid: str
    reward_per_sec: str
    reward_per_share: str
    tez_pool: str
    token_address: str
    token_id: str
    token_pool: str
    total_reward: str
    total_supply: str
    total_votes: str
    user_rewards: Dict[str, UserRewards]
    veto: str
    vetos: Dict[str, str]
    voters: Dict[str, Voters]
    votes: Dict[str, str]


class QuipuswapFa2FKBStorage(BaseModel):
    dex_lambdas: Dict[str, str]
    metadata: Dict[str, str]
    storage: Storage
    token_lambdas: Dict[str, str]
