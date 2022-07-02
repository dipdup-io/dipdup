import os
from unittest.mock import MagicMock

if os.environ.get('DEBUG'):
    from dipdup.cli import set_up_logging
    from dipdup.config import DipDupConfig
    from dipdup.config import LoggingValues

    set_up_logging()
    DipDupConfig.set_up_logging(MagicMock(logging=LoggingValues.verbose))
