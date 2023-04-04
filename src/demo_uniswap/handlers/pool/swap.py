from demo_uniswap import models as models
from demo_uniswap.types.pool.evm_events.swap import Swap
from dipdup.context import HandlerContext
from dipdup.models.evm_subsquid import SubsquidEvent


async def swap(
    ctx: HandlerContext,
    event: SubsquidEvent[Swap],
) -> None:
    ...