from typing import Dict

from dipdup.context import BigMapHandlerContext, HandlerContext, OperationHandlerContext
from dipdup.models import BigMapAction, BigMapData, BigMapDiff, OperationData, Origination, Transaction


async def on_configure(ctx: HandlerContext) -> None:
    ...
