# generated by datamodel-codegen:
#   filename:  storage.json

from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class MapItem(BaseModel):
    model_config = ConfigDict(extra='forbid')

    L: str


class MapItem1(BaseModel):
    model_config = ConfigDict(extra='forbid')

    R: str


class OrItem(BaseModel):
    model_config = ConfigDict(extra='forbid')

    L: str


class OrItem1(BaseModel):
    model_config = ConfigDict(extra='forbid')

    R: str


class BigMapItem(BaseModel):
    model_config = ConfigDict(extra='forbid')

    L: str


class BigMapItem1(BaseModel):
    model_config = ConfigDict(extra='forbid')

    R: str


class ZxcvStorage(BaseModel):
    model_config = ConfigDict(extra='forbid')

    map: dict[str, MapItem | MapItem1]
    unit: dict[str, Any]
    or_: OrItem | OrItem1 = Field(..., alias='or')
    big_map: dict[str, BigMapItem | BigMapItem1]
