from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class IndexStatus(str, Enum):
    idle = "idle"
    indexing = "indexing"
    error = "error"
    disabled = "disabled"
    completed = "completed"


class Index(BaseModel):
    name: str
    status: IndexStatus
    properties: Dict[str, Any] = Field(default_factory=dict)
    last_level: Optional[int] = None
    current_level: Optional[int] = None

    model_config = {"use_enum_values": False}
