import logging

from dipdup.context import BigMapHandlerContext, HandlerContext, OperationHandlerContext
from dipdup.models import BigMapAction, BigMapData, BigMapDiff, OperationData, Origination, Transaction

_logger = logging.getLogger(__name__)


from dipdup.context import HandlerContext


async def on_rollback(
    ctx: HandlerContext,
    from_level: int,
    to_level: int,
) -> None:
    _logger.warning('Rollback event received, reindexing')
    await ctx.reindex()
