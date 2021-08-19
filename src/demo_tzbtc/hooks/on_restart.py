from dipdup.context import HookContext
from dipdup.exceptions import CallbackNotImplementedError


async def on_restart(
    ctx: HookContext,
) -> None:
    await ctx.execute_sql('on_restart')
    raise CallbackNotImplementedError
