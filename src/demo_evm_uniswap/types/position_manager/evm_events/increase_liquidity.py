# generated by DipDup 8.1.1

from __future__ import annotations

from pydantic import BaseModel
from pydantic import ConfigDict


class IncreaseLiquidityPayload(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    tokenId: int
    liquidity: int
    amount0: int
    amount1: int
