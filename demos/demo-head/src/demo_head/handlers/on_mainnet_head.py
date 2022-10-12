
from dipdup.models import HeadBlockData
from dipdup.context import HandlerContext
from demo_head import models as models

async def on_mainnet_head(
    ctx: HandlerContext,
    head: HeadBlockData,
) -> None:
    ...