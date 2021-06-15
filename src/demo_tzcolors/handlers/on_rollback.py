import logging

from dipdup.context import RollbackHandlerContext

_logger = logging.getLogger(__name__)


async def on_rollback(ctx: RollbackHandlerContext) -> None:
    _logger.warning('Datasource `%s` rolled back from level %s to level %s, reindexing', ctx.datasource, ctx.from_level, ctx.to_level)
    await ctx.reindex()
