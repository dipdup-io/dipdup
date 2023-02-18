# generated by datamodel-codegen:
#   filename:  uniswapV3SwapCallback.json

from __future__ import annotations

from pydantic import BaseModel
from pydantic import Extra


class UniswapV3SwapCallback(BaseModel):
    class Config:
        extra = Extra.forbid

    amount0Delta: int
    amount1Delta: int
    data: str