from demo_uniswap import models as models
from demo_uniswap.types.factory.evm_events.pool_created import PoolCreated
from dipdup.context import HandlerContext
from dipdup.models.evm_subsquid import SubsquidEvent


async def pool_created(
    ctx: HandlerContext,
    event: SubsquidEvent[PoolCreated],
) -> None:
    ...
