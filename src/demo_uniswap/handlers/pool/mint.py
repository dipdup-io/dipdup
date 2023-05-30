import logging

from demo_uniswap import models
from demo_uniswap.types.pool.evm_events.mint import Mint
from demo_uniswap.utils.pool import PoolUpdateSign
from demo_uniswap.utils.pool import pool_update
from demo_uniswap.utils.repo import models_repo
from dipdup.context import HandlerContext
from dipdup.models.evm_subsquid import SubsquidEvent
from eth_utils.address import to_normalized_address


async def mint(
    ctx: HandlerContext,
    event: SubsquidEvent[Mint],
) -> None:
    pool = await models.Pool.cached_get_or_none(event.data.address)
    if not pool:
        ctx.logger.debug('Pool.mint: skipping pool %s as it is not in the cache', event.data.address)
        return

    await pool_update(ctx, pool, event, PoolUpdateSign.MINT)

    position_idx = f'{event.data.level}.{event.data.transaction_index}.{event.data.log_index + 1}'
    pending_position = dict(
        owner=to_normalized_address(event.payload.owner),
        pool_id=pool.id,
        token0_id=pool.token0_id,
        token1_id=pool.token1_id,
        tick_lower_id=f'{pool.id}#{event.payload.tickLower}',
        tick_upper_id=f'{pool.id}#{event.payload.tickUpper}'
    )
    models_repo.save_pending_position(position_idx, pending_position)
