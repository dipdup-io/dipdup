from demo_head import models as models
from dipdup.context import HandlerContext
from dipdup.models import HeadBlockData


async def on_mainnet_head(
    ctx: HandlerContext,
    head: HeadBlockData,
) -> None:
    ...
