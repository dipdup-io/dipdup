from demo_uniswap.types.position_manager.evm_events.collect import Collect
from demo_uniswap.utils.position import position_get_or_create
from demo_uniswap.utils.position import save_position_snapshot
from demo_uniswap.utils.repo import models_repo
from demo_uniswap.utils.token import convert_token_amount
from dipdup.context import HandlerContext
from dipdup.models.evm_subsquid import SubsquidEvent

BLACKLISTED_POOLS = {'0x8fe8d9bb8eeba3ed688069c3d6b556c9ca258248'}


async def collect(
    ctx: HandlerContext,
    event: SubsquidEvent[Collect],
) -> None:
    position = await position_get_or_create(ctx, event.data.address, event.payload.tokenId)
    if not position:
        ctx.logger.debug('Position is none (tokenId %d)', event.payload.tokenId)
        return

    if position.pool in BLACKLISTED_POOLS:
        ctx.logger.debug('Blacklisted pool %s', position.pool)
        return

    token0 = await models_repo.get_token(position.token0_id)
    amount0 = convert_token_amount(event.payload.amount0, token0.decimals)
    amount1 = convert_token_amount(event.payload.amount1, token0.decimals)  # Correct?

    position.collected_fees_token0 += amount0
    position.collected_fees_token1 += amount1

    await models_repo.update_position(position)
    await save_position_snapshot(position, event.data.level)
