from demo_uniswap import models
from dipdup.context import HookContext


async def on_reindex(
    ctx: HookContext,
) -> None:
    # NOTE: Positions table is immune to decrease node usage, but we need to reset counters
    await ctx.execute_sql('on_reindex')
    await models.Position.reset()
