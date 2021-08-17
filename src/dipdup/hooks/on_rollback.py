
from dipdup.context import HookContext
from dipdup.datasources.datasource import Datasource

async def on_rollback(
    ctx: HookContext,
    datasource: Datasource,
    from_level: int,
    to_level: int,
) -> None:
    ctx.logger.warning('Datasource `%s` rolled back from level %s to level %s, reindexing', datasource, from_level, to_level)
    await ctx.reindex()
