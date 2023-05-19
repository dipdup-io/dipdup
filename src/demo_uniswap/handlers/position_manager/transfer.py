from demo_uniswap.types.position_manager.evm_events.transfer import Transfer
from demo_uniswap.utils.position import position_get_or_create
from demo_uniswap.utils.position import save_position_snapshot
from dipdup.context import HandlerContext
from dipdup.models.evm_subsquid import SubsquidEvent


async def transfer(
    ctx: HandlerContext,
    event: SubsquidEvent[Transfer],
) -> None:
    position = await position_get_or_create(ctx, event.data.address, event.payload.tokenId)
    if not position:
        ctx.logger.debug('Position is none (tokenId %d)', event.payload.tokenId)
        return

    position.owner = event.payload.to

    await position.save()
    await save_position_snapshot(position, event.data.level)
