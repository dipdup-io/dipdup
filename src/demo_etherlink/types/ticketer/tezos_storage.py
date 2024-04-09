# generated by DipDup 7.5.3

from __future__ import annotations

from pydantic import BaseModel
from pydantic import ConfigDict


class Content(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    nat: str
    bytes: str | None = None


class Token(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    fa12: str


class Fa2(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    address: str
    nat: str


class Token1(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    fa2: Fa2


class TicketerStorage(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    content: Content
    metadata: dict[str, str]
    token: Token | Token1
