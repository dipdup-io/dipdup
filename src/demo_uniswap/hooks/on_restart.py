from demo_uniswap.utils.position import restore_cache
from dipdup.context import HookContext
import logging


async def on_restart(
    ctx: HookContext,
) -> None:
    logging.getLogger('aiosqlite').setLevel(logging.DEBUG)
    await ctx.execute_sql('on_restart')
    await restore_cache()
