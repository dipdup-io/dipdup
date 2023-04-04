from demo_uniswap import models as models
from demo_uniswap.types.position_manager.evm_events.decrease_liquidity import DecreaseLiquidity
from dipdup.context import HandlerContext
from dipdup.models.evm_subsquid import SubsquidEvent


async def decrease_liquidity(
    ctx: HandlerContext,
    event: SubsquidEvent[DecreaseLiquidity],
) -> None:
    ...