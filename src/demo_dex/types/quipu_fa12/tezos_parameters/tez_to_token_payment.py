# generated by DipDup 7.5.4

from __future__ import annotations

from pydantic import BaseModel
from pydantic import ConfigDict


class TezToTokenPaymentParameter(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    min_out: str
    receiver: str
