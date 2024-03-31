from demo_uniswap import models as models
from demo_uniswap.types.pool.evm_events.flash import Flash
from dipdup.context import HandlerContext
from dipdup.models.evm_subsquid import EvmSubsquidEvent


async def flash(
    ctx: HandlerContext,
    event: EvmSubsquidEvent[Flash],
) -> None:
    ...