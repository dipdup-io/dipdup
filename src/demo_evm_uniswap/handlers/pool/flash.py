from demo_evm_uniswap import models as models
from demo_evm_uniswap.types.pool.evm_events.flash import FlashPayload
from dipdup.context import HandlerContext
from dipdup.models.evm import EvmEvent


async def flash(
    ctx: HandlerContext,
    event: EvmEvent[FlashPayload],
) -> None: ...
