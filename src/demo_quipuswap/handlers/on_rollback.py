from dipdup.context import RollbackHandlerContext


async def on_rollback(ctx: RollbackHandlerContext) -> None:
    ctx.logger.warning('Datasource `%s` rolled back from level %s to level %s, reindexing', ctx.datasource, ctx.from_level, ctx.to_level)
    await ctx.reindex()
