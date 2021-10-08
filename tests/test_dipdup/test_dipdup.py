import logging
from contextlib import AsyncExitStack
from os.path import dirname, join
from unittest import IsolatedAsyncioTestCase

from dipdup.config import DipDupConfig, SqliteDatabaseConfig
from dipdup.context import pending_indexes
from dipdup.dipdup import DipDup, IndexDispatcher
from dipdup.models import Index

logging.basicConfig(level=logging.DEBUG)


async def _create_dipdup(config: DipDupConfig, stack: AsyncExitStack) -> DipDup:
    config.database = SqliteDatabaseConfig(kind='sqlite', path=':memory:')
    config.initialize(skip_imports=True)

    dipdup = DipDup(config)
    await dipdup._create_datasources()
    await dipdup._set_up_database(stack, False)
    await dipdup._set_up_hooks()
    await dipdup._initialize_schema()
    return dipdup


async def _spawn_index(dispatcher: IndexDispatcher, name: str) -> None:
    await dispatcher._ctx._spawn_index(name)
    dispatcher._indexes[name] = pending_indexes.pop()


class IndexStateTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        name = 'hic_et_nunc.yml'
        config_path = join(dirname(__file__), '..', 'integration_tests', name)
        self.config = DipDupConfig.load([config_path])

        self.new_hash = '32e3aaf18a45acf090bea833fd89a71c9b50cefcc7d859ff7faf9e1d5ebb5938'
        self.old_hash = ''

    async def test_first_run(self) -> None:
        async with AsyncExitStack() as stack:
            # Arrange
            dipdup = await _create_dipdup(self.config, stack)
            dispatcher = IndexDispatcher(dipdup._ctx)

            # Act
            await _spawn_index(dispatcher, 'hen_mainnet')

            # Assert
            index = await Index.filter().get()
            self.assertEqual(self.new_hash, index.config_hash)
