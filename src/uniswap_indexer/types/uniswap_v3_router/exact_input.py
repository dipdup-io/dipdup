# generated by datamodel-codegen:
#   filename:  exactInput.json

from __future__ import annotations

from typing import Any
from typing import Dict

from pydantic import BaseModel
from pydantic import Extra


class ExactInput(BaseModel):
    class Config:
        extra = Extra.forbid

    params: Dict[str, Any]
