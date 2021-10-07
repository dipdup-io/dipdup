from dipdup.context import HookContext
from dipdup.datasources.datasource import Datasource
from dipdup.enums import ReindexingReason


async def on_rollback(
    ctx: HookContext,
    datasource: Datasource,
    from_level: int,
    to_level: int,
) -> None:
    await ctx.execute_sql('on_rollback')
    await ctx.reindex(ReindexingReason.ROLLBACK)
