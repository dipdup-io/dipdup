# generated by datamodel-codegen:
#   filename:  redeem.json

from __future__ import annotations

from pydantic import BaseModel
from pydantic import Extra


class Redeem(BaseModel):
    class Config:
        extra = Extra.forbid

    amount: int
