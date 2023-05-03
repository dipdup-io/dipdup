from demo_uniswap.types.pool.evm_events.burn import Burn
from demo_uniswap.utils.pool import PoolUpdateSign
from demo_uniswap.utils.pool import pool_update
from dipdup.context import HandlerContext
from dipdup.models.evm_subsquid import SubsquidEvent


async def burn(
    ctx: HandlerContext,
    event: SubsquidEvent[Burn],
) -> None:
    await pool_update(ctx, event, PoolUpdateSign.BURN)
