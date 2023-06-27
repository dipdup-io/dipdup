from demo_head import models as models
from dipdup.context import HandlerContext
from dipdup.models.tezos_tzkt import TzktHeadBlockData


async def on_mainnet_head(
    ctx: HandlerContext,
    head: TzktHeadBlockData,
) -> None:
    ...