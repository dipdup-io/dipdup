from demo_uniswap import models
from demo_uniswap.types.pool.evm_events.mint import Mint
from demo_uniswap.utils.pool import PoolUpdateSign
from demo_uniswap.utils.pool import pool_update
from demo_uniswap.utils.position import position_mint, position_skip
from dipdup.context import HandlerContext
from dipdup.models.evm_subsquid import SubsquidEvent
from eth_utils.address import to_normalized_address


async def mint(
    ctx: HandlerContext,
    event: SubsquidEvent[Mint],
) -> None:
    pool = await models.Pool.cached_get_or_none(event.data.address)
    if not pool:
        print('Pool.mint: skipping pool %s as it is not in the cache', event.data.address)
        skip = True
    else:
        await pool_update(ctx, pool, event, PoolUpdateSign.MINT)
        skip = False
    await position_mint(
        ctx,
        to_normalized_address(event.payload.owner),
        pool.id,
        pool.token0_id,
        pool.token1_id,
        f'{pool.id}#{event.payload.tickLower}',
        f'{pool.id}#{event.payload.tickUpper}',
        save=not skip
    )
