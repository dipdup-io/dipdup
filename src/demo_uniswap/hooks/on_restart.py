from demo_uniswap.utils.repo import models_repo
from dipdup.context import HookContext


async def on_restart(
    ctx: HookContext,
) -> None:
    await ctx.execute_sql('on_restart')
    ctx.caches.add_plain(models_repo._pending_positions, 'pending_positions')
