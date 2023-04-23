from demo_uniswap.utils.repo import models_repo
from demo_uniswap.utils.token import convert_token_amount
from demo_uniswap.types.position_manager.evm_events.increase_liquidity import IncreaseLiquidity
from dipdup.context import HandlerContext
from dipdup.models.evm_subsquid import SubsquidEvent
from demo_uniswap.utils.position import position_get_or_create, save_position_snapshot

BLACKLISTED_BLOCKS = {14317993}
BLACKLISTED_POOLS = {'0x8fe8d9bb8eeba3ed688069c3d6b556c9ca258248'}


async def increase_liquidity(
    ctx: HandlerContext,
    event: SubsquidEvent[IncreaseLiquidity],
) -> None:
    if event.data.level in BLACKLISTED_BLOCKS:
        ctx.logger.debug('Blacklisted level %d', event.data.level)
        return

    position = await position_get_or_create(ctx, event.data.address, event.payload.tokenId)
    if not position:
        ctx.logger.debug('Position is none (tokenId %d)', event.payload.tokenId)
        return

    if position.pool in BLACKLISTED_POOLS:
        ctx.logger.debug('Blacklisted pool %s', position.pool)
        return

    token0 = await models_repo.get_token(position.token0_id)  # FIXME: typing
    token1 = await models_repo.get_token(position.token1_id)  # FIXME: typing

    amount0 = convert_token_amount(event.payload.amount0, token0.decimals)
    amount1 = convert_token_amount(event.payload.amount1, token1.decimals)

    position.liquidity += event.payload.liquidity
    position.deposited_token0 += amount0
    position.deposited_token1 += amount1

    await models_repo.update_position(position)
    await save_position_snapshot(position, event.data.level)
