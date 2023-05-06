from demo_uniswap.types.pool.evm_events.mint import Mint
from demo_uniswap.utils.pool import PoolUpdateSign
from demo_uniswap.utils.pool import pool_update
from dipdup.context import HandlerContext
from dipdup.models.evm_subsquid import SubsquidEvent


async def mint(
    ctx: HandlerContext,
    event: SubsquidEvent[Mint],
) -> None:
    await pool_update(ctx, event, PoolUpdateSign.MINT)
