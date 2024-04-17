from decimal import Decimal

from demo_evm_uniswap import models
from demo_evm_uniswap.models.token import token_derive_eth
from demo_evm_uniswap.types.pool.evm_logs.initialize import InitializePayload
from dipdup.context import HandlerContext
from dipdup.models.evm import EvmLog


async def initialize(
    ctx: HandlerContext,
    log: EvmLog[InitializePayload],
) -> None:
    pool = await models.Pool.cached_get_or_none(log.data.address)
    if not pool:
        return
    pool.sqrt_price = Decimal(log.payload.sqrtPriceX96)
    pool.tick = log.payload.tick
    await pool.save()

    token0 = await models.Token.cached_get(pool.token0_id)
    token1 = await models.Token.cached_get(pool.token1_id)
    token0.derived_eth = await token_derive_eth(token0)
    token1.derived_eth = await token_derive_eth(token1)
    await token0.save()
    await token1.save()