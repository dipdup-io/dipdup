# generated by datamodel-codegen:
#   filename:  IncreaseLiquidity.json

from __future__ import annotations

from pydantic import BaseModel
from pydantic import Extra


class IncreaseLiquidity(BaseModel):
    class Config:
        extra = Extra.forbid

    tokenId: int
    liquidity: int
    amount0: int
    amount1: int
