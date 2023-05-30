from demo_uniswap import models
from demo_uniswap.types.position_manager.evm_events.decrease_liquidity import DecreaseLiquidity
from demo_uniswap.utils.position import save_position_snapshot
from demo_uniswap.utils.token import convert_token_amount
from dipdup.context import HandlerContext
from dipdup.models.evm_subsquid import SubsquidEvent

BLACKLISTED_BLOCKS = {14317993}
BLACKLISTED_POOLS = {'0x8fe8d9bb8eeba3ed688069c3d6b556c9ca258248'}


async def decrease_liquidity(
    ctx: HandlerContext,
    event: SubsquidEvent[DecreaseLiquidity],
) -> None:
    if event.data.level in BLACKLISTED_BLOCKS:
        ctx.logger.debug('Blacklisted level %d', event.data.level)
        return

    position = await models.Position.get(id=event.payload.tokenId)
    if position.pool in BLACKLISTED_POOLS:
        ctx.logger.debug('Blacklisted pool %s', position.pool)
        return

    token0 = await models.Token.cached_get(position.token0_id)
    token1 = await models.Token.cached_get(position.token1_id)

    amount0 = convert_token_amount(event.payload.amount0, token0.decimals)
    amount1 = convert_token_amount(event.payload.amount1, token1.decimals)

    position.liquidity -= event.payload.liquidity
    position.withdrawn_token0 += amount0
    position.withdrawn_token1 += amount1

    await position.save()
    # position.cache()
    await save_position_snapshot(position, event.data.level)
