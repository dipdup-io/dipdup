from demo_uniswap import models
from demo_uniswap.types.pool.evm_events.mint import Mint
from demo_uniswap.utils.pool import PoolUpdateSign
from demo_uniswap.utils.pool import pool_update
from dipdup.context import HandlerContext
from dipdup.models.evm_subsquid import SubsquidEvent


async def mint(
    ctx: HandlerContext,
    event: SubsquidEvent[Mint],
) -> None:
    pool = await models.Pool.cached_get_or_none(event.data.address)
    if not pool:
        return
    await pool_update(ctx, pool, event, PoolUpdateSign.MINT)
