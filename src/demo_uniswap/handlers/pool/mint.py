from demo_uniswap import models as models
from demo_uniswap.types.pool.evm_events.mint import Mint
from dipdup.context import HandlerContext
from dipdup.models.evm_subsquid import SubsquidEvent


async def mint(
    ctx: HandlerContext,
    event: SubsquidEvent[Mint],
) -> None:
    ...