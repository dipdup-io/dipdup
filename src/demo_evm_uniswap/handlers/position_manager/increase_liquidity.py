from demo_evm_uniswap import models
from demo_evm_uniswap.models.position import save_position_snapshot
from demo_evm_uniswap.models.token import convert_token_amount
from demo_evm_uniswap.types.position_manager.evm_logs.increase_liquidity import IncreaseLiquidityPayload
from dipdup.context import HandlerContext
from dipdup.models.evm import EvmLog

BLACKLISTED_BLOCKS = {14317993}


async def increase_liquidity(
    ctx: HandlerContext,
    log: EvmLog[IncreaseLiquidityPayload],
) -> None:
    if log.data.level in BLACKLISTED_BLOCKS:
        ctx.logger.warning('Blacklisted level %d', log.data.level)
        return

    position = await models.Position.get_or_none(id=log.payload.tokenId)
    if position is None:
        ctx.logger.warning('Skipping position %s (must be blacklisted pool)', log.payload.tokenId)
        return

    # TODO: remove me
    # await position_validate(ctx, log.data.address, log.payload.tokenId, position)

    token0 = await models.Token.cached_get(position.token0_id)
    token1 = await models.Token.cached_get(position.token1_id)

    amount0 = convert_token_amount(log.payload.amount0, token0.decimals)
    amount1 = convert_token_amount(log.payload.amount1, token1.decimals)

    position.liquidity += log.payload.liquidity
    position.deposited_token0 += amount0
    position.deposited_token1 += amount1

    await position.save()
    await save_position_snapshot(position, log.data.level, log.data.timestamp)