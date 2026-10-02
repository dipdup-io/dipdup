from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from dipdup.context import DipDupContext
from dipdup.models.index import IndexStatus

router = APIRouter()


class UpdateIndexPayload(BaseModel):
    status: IndexStatus | None = None
    properties: dict | None = None


@router.patch("/{name}")
async def update_index(
    name: str,
    payload: UpdateIndexPayload,
    context: DipDupContext,
):
    try:
        index = await context.update_index(
            name,
            status=payload.status,
            properties=payload.properties,
        )
        return index
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Index {name} not found")
