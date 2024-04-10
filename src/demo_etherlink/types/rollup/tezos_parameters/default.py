# generated by DipDup 7.5.4

from __future__ import annotations

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import RootModel


class Data(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    nat: str
    bytes: str | None = None


class Ticket(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    address: str
    data: Data
    amount: str


class LL(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    bytes: str
    ticket: Ticket


class DefaultParameter1(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    LL: LL


class DefaultParameter2(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    LR: str


class DefaultParameter3(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    R: str


class DefaultParameter(RootModel[DefaultParameter1 | DefaultParameter2 | DefaultParameter3]):
    root: DefaultParameter1 | DefaultParameter2 | DefaultParameter3
