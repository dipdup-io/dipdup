from demo_starknet_events import models as models
from demo_starknet_events.types.stark_usdc.starknet_events.transfer import TransferPayload
from dipdup.context import HandlerContext
from dipdup.models.starknet import StarknetEvent


async def on_transfer(
    ctx: HandlerContext,
    event: StarknetEvent[TransferPayload],
) -> None:
    ...