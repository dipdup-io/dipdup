from demo_evm_uniswap import models as models
from demo_evm_uniswap.types.pool.evm_logs.flash import FlashPayload
from dipdup.context import HandlerContext
from dipdup.models.evm import EvmLog


async def flash(
    ctx: HandlerContext,
    log: EvmLog[FlashPayload],
) -> None:
    ...