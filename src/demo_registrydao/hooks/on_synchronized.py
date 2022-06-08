from dipdup.context import HookContext


async def on_synchronized(
    ctx: HookContext,
) -> None:
    await ctx.execute_sql_scripts('on_synchronized')
