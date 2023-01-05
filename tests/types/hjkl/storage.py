# generated by datamodel-codegen:
#   filename:  storage.json

from __future__ import annotations

from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Extra


class Key(BaseModel):
    class Config:
        extra = Extra.forbid

    string: str
    nat: str


class Value(BaseModel):
    class Config:
        extra = Extra.forbid

    sw: Optional[str]
    mr: Optional[Dict[str, bool]]


class HjklStorageItem(BaseModel):
    class Config:
        extra = Extra.forbid

    key: Key
    value: Value


class HjklStorage(BaseModel):
    __root__: List[HjklStorageItem]