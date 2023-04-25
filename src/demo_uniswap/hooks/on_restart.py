from dipdup.context import HookContext


async def on_restart(
    ctx: HookContext,
) -> None:
    await ctx.execute_sql('on_restart')

    if ctx.config.database.kind != 'postgres':
        raise Exception('Python int too large to convert to SQLite INTEGER; use postgres instead')