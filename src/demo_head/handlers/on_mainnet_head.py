from demo_head import models as models
from dipdup.context import HandlerContext
from dipdup.models.tezos_tzkt import TezosTzktHeadBlockData as HeadBlockData


async def on_mainnet_head(
    ctx: HandlerContext,
    head: HeadBlockData,
) -> None:
    ...