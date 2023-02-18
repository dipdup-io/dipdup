# generated by datamodel-codegen:
#   filename:  sweepTokenWithFee.json

from __future__ import annotations

from pydantic import BaseModel
from pydantic import Extra


class SweepTokenWithFee(BaseModel):
    class Config:
        extra = Extra.forbid

    token: str
    amountMinimum: int
    recipient: str
    feeBips: int
    feeRecipient: str