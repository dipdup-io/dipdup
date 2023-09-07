# 1. start sync
# 2. open realtime connection
# 3. receive a message or two
# 4. finish sync
# 5. check for missing operations
from contextlib import AsyncExitStack

from dipdup.config import DipDupConfig
from dipdup.config import SqliteDatabaseConfig
from dipdup.dipdup import DipDup


async def create_dummy_dipdup(
    config: DipDupConfig,
    stack: AsyncExitStack,
    in_memory: bool = False,
) -> 'DipDup':
    """Create a dummy DipDup instance for testing purposes.

    Only basic initialization is performed:

    - Create datasources without spawning them
    - Register system hooks
    - Initialize Tortoise ORM and create schema

    You need to enter `AsyncExitStack` context manager prior to calling this method.
    """
    if in_memory:
        config.database = SqliteDatabaseConfig(
            kind='sqlite',
            path=':memory:',
        )
    config.advanced.rollback_depth = 2
    config.initialize()

    dipdup = DipDup(config)
    await dipdup._create_datasources()
    await dipdup._set_up_database(stack)
    await dipdup._set_up_hooks(set())
    await dipdup._initialize_schema()
    await dipdup._set_up_transactions(stack)

    return dipdup
