from demo_uniswap import models as models
from demo_uniswap.types.pool.evm_events.initialize import Initialize
from dipdup.context import HandlerContext
from dipdup.models.evm_subsquid import SubsquidEvent


async def initialize(
    ctx: HandlerContext,
    event: SubsquidEvent[Initialize],
) -> None:
    ...