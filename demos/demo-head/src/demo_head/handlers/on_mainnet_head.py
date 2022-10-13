
from demo_head import models as models
from dipdup.models import HeadBlockData
from dipdup.context import HandlerContext

async def on_mainnet_head(
    ctx: HandlerContext,
    head: HeadBlockData,
) -> None:
    ...