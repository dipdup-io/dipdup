import logging
import os
import sys

from tortoise import Tortoise

_logger = logging.getLogger(__name__)


async def on_rollback(
    from_level: int,
    to_level: int,
) -> None:
    _logger.warning('Rollback event received, reindexing')
    await Tortoise._drop_databases()
    os.execl(sys.executable, sys.executable, *sys.argv)
