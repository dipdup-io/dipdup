from demo_uniswap import models as models
from demo_uniswap.types.pool.evm_logs.flash import Flash
from dipdup.context import HandlerContext
from dipdup.models.evm import EvmLog


async def flash(
    ctx: HandlerContext,
    event: EvmLog[Flash],
) -> None:
    ...