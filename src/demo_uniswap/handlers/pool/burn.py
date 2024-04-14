from demo_uniswap import models
from demo_uniswap.models.pool import PoolUpdateSign
from demo_uniswap.models.pool import pool_update
from demo_uniswap.types.pool.evm_logs.burn import Burn
from dipdup.context import HandlerContext
from dipdup.models.evm import EvmLog


async def burn(
    ctx: HandlerContext,
    event: EvmLog[Burn],
) -> None:
    pool = await models.Pool.cached_get_or_none(event.data.address)
    if not pool:
        return
    await pool_update(ctx, pool, event, PoolUpdateSign.BURN)