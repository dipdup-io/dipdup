from dipdup.context import HookContext
from dipdup.enums import ReindexingReason
from dipdup.index import Index


async def on_index_rollback(
    ctx: HookContext,
    index: Index,
    from_level: int,
    to_level: int,
) -> None:
    await ctx.execute_sql('on_index_rollback')
    await ctx.reindex(
        ReindexingReason.rollback,
        index=index.name,
        datasource=index.datasource.name,
        from_level=from_level,
        to_level=to_level,
    )
