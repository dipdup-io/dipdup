# generated by datamodel-codegen:
#   filename:  mint.json

from __future__ import annotations

from pydantic import BaseModel


class Mint(BaseModel):
    address: str
    value: str
