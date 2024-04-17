from demo_evm_uniswap import models
from demo_evm_uniswap.models.pool import PoolUpdateSign
from demo_evm_uniswap.models.pool import pool_update
from demo_evm_uniswap.types.pool.evm_logs.burn import BurnPayload
from dipdup.context import HandlerContext
from dipdup.models.evm import EvmLog


async def burn(
    ctx: HandlerContext,
    log: EvmLog[BurnPayload],
) -> None:
    pool = await models.Pool.cached_get_or_none(log.data.address)
    if not pool:
        return
    await pool_update(ctx, pool, log, PoolUpdateSign.BURN)