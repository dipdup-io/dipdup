# generated by datamodel-codegen:
#   filename:  storage.json

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class Admin(BaseModel):
    admin: str
    paused: bool
    pending_admin: Optional[str]


class Key(BaseModel):
    address_0: str
    address_1: str
    nat: str


class Operator(BaseModel):
    key: Key
    value: Dict[str, Any]


class TokenMetadata(BaseModel):
    token_id: str
    token_info: Dict[str, str]


class Assets(BaseModel):
    ledger: Dict[str, str]
    operators: List[Operator]
    token_metadata: Dict[str, TokenMetadata]
    total_supply: str


class TokenTChickenStorage(BaseModel):
    admin: Admin
    assets: Assets
    metadata: Dict[str, str]
