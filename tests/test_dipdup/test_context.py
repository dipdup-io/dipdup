from contextlib import AsyncExitStack
from os.path import dirname, join
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock

import dipdup.context as context
from dipdup.config import DipDupConfig, SqliteDatabaseConfig
from dipdup.dipdup import DipDup
from dipdup.enums import ReindexingReason
from dipdup.exceptions import ReindexingRequiredError
from dipdup.models import Schema


async def _create_dipdup(config: DipDupConfig, stack: AsyncExitStack) -> DipDup:
    config.database = SqliteDatabaseConfig(kind='sqlite', path=':memory:')
    config.initialize(skip_imports=True)

    dipdup = DipDup(config)
    await dipdup._create_datasources()
    await dipdup._set_up_database(stack, False)
    await dipdup._set_up_hooks()
    await dipdup._initialize_schema()
    return dipdup


class ConfigTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.path = join(dirname(__file__), 'dipdup.yml')

    async def test_reindex_manual_forbidden(self):
        async with AsyncExitStack() as stack:
            # Arrange
            context.forbid_reindexing = True
            config = DipDupConfig.load([self.path])
            dipdup = await _create_dipdup(config, stack)

            # Act
            with self.assertRaises(ReindexingRequiredError):
                await dipdup._ctx.reindex()

            # Assert
            schema = await Schema.filter().get()
            self.assertEqual(ReindexingReason.MANUAL, schema.reindex)

    async def test_reindex_manual_allowed(self):
        async with AsyncExitStack() as stack:
            # Arrange
            context.forbid_reindexing = False
            config = DipDupConfig.load([self.path])
            dipdup = await _create_dipdup(config, stack)
            dipdup._ctx.restart = AsyncMock()

            # Act
            await dipdup._ctx.reindex()

            # Assert
            dipdup._ctx.restart.assert_awaited()

            with self.assertRaises(Exception):
                schema = await Schema.filter().get()

            await _create_dipdup(config, stack)
            schema = await Schema.filter().get()
            self.assertEqual(None, schema.reindex)

    async def test_reindex_field(self):
        async with AsyncExitStack() as stack:
            # Arrange
            context.forbid_reindexing = True
            config = DipDupConfig.load([self.path])
            dipdup = await _create_dipdup(config, stack)

            await Schema.filter().update(reindex=ReindexingReason.MANUAL)

            # Act
            with self.assertRaises(ReindexingRequiredError):
                await dipdup._initialize_schema()

            # Assert
            schema = await Schema.filter().get()
            self.assertEqual(ReindexingReason.MANUAL, schema.reindex)
