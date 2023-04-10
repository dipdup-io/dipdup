from demo_uniswap import models as models
from demo_uniswap.types.position_manager.evm_events.increase_liquidity import IncreaseLiquidity
from dipdup.context import HandlerContext
from dipdup.models.evm_subsquid import SubsquidEvent


async def increase_liquidity(
    ctx: HandlerContext,
    event: SubsquidEvent[IncreaseLiquidity],
) -> None:
    ...
