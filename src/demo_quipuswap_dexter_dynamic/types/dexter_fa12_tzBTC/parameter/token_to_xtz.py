# generated by datamodel-codegen:
#   filename:  tokenToXtz.json

from __future__ import annotations

from pydantic import BaseModel


class TokenToXtzParameter(BaseModel):
    owner: str
    to: str
    tokensSold: str
    minXtzBought: str
    deadline: str
