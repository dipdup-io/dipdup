from dipdup.context import HookContext


async def on_restart(
    ctx: HookContext,
) -> None:
    await ctx.execute_sql_scripts('on_restart')
