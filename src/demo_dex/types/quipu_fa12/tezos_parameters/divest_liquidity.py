# generated by DipDup 7.5.4

from __future__ import annotations

from pydantic import BaseModel
from pydantic import ConfigDict


class DivestLiquidityParameter(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    min_tez: str
    min_tokens: str
    shares: str
