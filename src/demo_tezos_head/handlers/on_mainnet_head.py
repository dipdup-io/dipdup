from demo_tezos_head import models as models
from dipdup.context import HandlerContext
from dipdup.models.tezos import TezosHeadBlockData


async def on_mainnet_head(
    ctx: HandlerContext,
    head: TezosHeadBlockData,
) -> None: ...
