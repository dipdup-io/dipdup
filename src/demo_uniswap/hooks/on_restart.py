from demo_uniswap.utils.position import restore_cache
from dipdup.context import HookContext


async def on_restart(
    ctx: HookContext,
) -> None:
    await ctx.execute_sql('on_restart')
    await restore_cache()
