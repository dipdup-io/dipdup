# generated by datamodel-codegen:
#   filename:  storage.json

from __future__ import annotations

from typing import Dict

from pydantic import BaseModel
from pydantic import Extra


class Royalties(BaseModel):
    class Config:
        extra = Extra.forbid

    issuer: str
    royalties: str


class Swaps(BaseModel):
    class Config:
        extra = Extra.forbid

    issuer: str
    objkt_amount: str
    objkt_id: str
    xtz_per_objkt: str


class HenMinterStorage(BaseModel):
    class Config:
        extra = Extra.forbid

    curate: str
    genesis: str
    hdao: str
    locked: bool
    manager: str
    metadata: Dict[str, str]
    objkt: str
    objkt_id: str
    royalties: Dict[str, Royalties]
    size: str
    swap_id: str
    swaps: Dict[str, Swaps]
