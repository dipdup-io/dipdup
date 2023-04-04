from demo_uniswap import models as models
from demo_uniswap.types.pool.evm_events.burn import Burn
from dipdup.context import HandlerContext
from dipdup.models.evm_subsquid import SubsquidEvent


async def burn(
    ctx: HandlerContext,
    event: SubsquidEvent[Burn],
) -> None:
    ...