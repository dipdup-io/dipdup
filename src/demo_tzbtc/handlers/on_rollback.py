import logging

from dipdup.utils import reindex

_logger = logging.getLogger(__name__)


async def on_rollback(
    from_level: int,
    to_level: int,
) -> None:
    if from_level - to_level == 1:
        return
    _logger.warning('Rollback event received, reindexing')
    await reindex()
