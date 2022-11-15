import os
from contextlib import AsyncExitStack
from pathlib import Path
from unittest.mock import MagicMock

from dipdup.config import DipDupConfig
from dipdup.config import SqliteDatabaseConfig
from dipdup.dipdup import DipDup

os.environ['REPLAY_PATH'] = str(Path(__file__).parent / 'replays')

if os.environ.get('DEBUG'):
    from dipdup.cli import set_up_logging
    from dipdup.config import LoggingValues

    set_up_logging()
    DipDupConfig.set_up_logging(MagicMock(logging=LoggingValues.verbose))


async def create_test_dipdup(config: DipDupConfig, stack: AsyncExitStack) -> DipDup:
    config.database = SqliteDatabaseConfig(kind='sqlite', path=':memory:')
    config.initialize(skip_imports=True)

    dipdup = DipDup(config)
    await dipdup._create_datasources()
    await dipdup._set_up_database(stack)
    await dipdup._set_up_hooks(set())
    await dipdup._initialize_schema()
    return dipdup
