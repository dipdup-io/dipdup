# generated by datamodel-codegen:
#   filename:  tezos_storage.json

from __future__ import annotations

from pydantic import BaseModel
from pydantic import Extra


class Token(BaseModel):
    class Config:
        extra = Extra.forbid

    fa12: str


class Fa2(BaseModel):
    class Config:
        extra = Extra.forbid

    address: str
    nat: str


class Token1(BaseModel):
    class Config:
        extra = Extra.forbid

    fa2: Fa2


class Context(BaseModel):
    class Config:
        extra = Extra.forbid

    routing_info: str
    rollup: str


class TicketHelperStorage(BaseModel):
    class Config:
        extra = Extra.forbid

    token: Token | Token1
    ticketer: str
    context: Context | None
    metadata: dict[str, str]
