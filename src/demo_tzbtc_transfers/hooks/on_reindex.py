from dipdup.context import HookContext


async def on_reindex(
    ctx: HookContext,
) -> None:
    await ctx.execute_sql_scripts('on_reindex')
