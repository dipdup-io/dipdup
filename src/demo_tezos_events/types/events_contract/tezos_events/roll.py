# generated by DipDup 8.0.0b3

from __future__ import annotations

from pydantic import BaseModel
from pydantic import ConfigDict


class RollPayload(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    address: str
    bool: bool
