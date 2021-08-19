from dipdup.context import HookContext
from dipdup.exceptions import CallbackNotImplementedError


async def on_reindex(
    ctx: HookContext,
) -> None:
    await ctx.execute_sql('on_reindex')
    raise CallbackNotImplementedError
