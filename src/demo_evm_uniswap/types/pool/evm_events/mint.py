# generated by DipDup 8.0.0b2

from __future__ import annotations

from pydantic import BaseModel
from pydantic import ConfigDict


class MintPayload(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    sender: str
    owner: str
    tickLower: int
    tickUpper: int
    amount: int
    amount0: int
    amount1: int
