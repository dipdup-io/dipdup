from demo_uniswap import models as models
from demo_uniswap.types.position_manager.evm_events.collect import Collect
from dipdup.context import HandlerContext
from dipdup.models.evm_subsquid import SubsquidEvent


async def collect(
    ctx: HandlerContext,
    event: SubsquidEvent[Collect],
) -> None:
    ...