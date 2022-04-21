from dipdup.context import HookContext
from dipdup.datasources.datasource import IndexDatasource
from dipdup.enums import ReindexingReason


async def on_rollback(
    ctx: HookContext,
    datasource: IndexDatasource,
    from_level: int,
    to_level: int,
) -> None:
    await ctx.execute_sql('on_rollback')
    await ctx.reindex(
        ReindexingReason.rollback,
        datasource=datasource.name,
        from_level=from_level,
        to_level=to_level,
    )
