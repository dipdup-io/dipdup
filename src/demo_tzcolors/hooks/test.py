
from dipdup.context import HookContext
from dipdup.exceptions import CallbackNotImplementedError

async def test(
    ctx: HookContext,
) -> None:
    await ctx.execute_sql('test')