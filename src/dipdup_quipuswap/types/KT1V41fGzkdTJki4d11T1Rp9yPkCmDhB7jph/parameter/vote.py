# generated by datamodel-codegen:
#   filename:  vote.json

from __future__ import annotations

from pydantic import BaseModel


class Vote(BaseModel):
    candidate: str
    value: str
    voter: str
