from typing import Any

from dipdup.config import HandlerConfig
from dipdup.context import HandlerContext
from dipdup.index import Index


async def batch(
    ctx: HandlerContext,
    handlers: tuple[tuple[Index[Any, Any, Any], HandlerConfig, Any]],
) -> None:
    for index, handler, data in handlers:
        await index._call_matched_handler(handler, data)