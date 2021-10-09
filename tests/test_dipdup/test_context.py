from contextlib import AsyncExitStack
from os.path import dirname, join
from unittest import IsolatedAsyncioTestCase, skip
from unittest.mock import AsyncMock

from tortoise.exceptions import ConfigurationError
from tortoise.transactions import get_connection

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


class ReindexingTest(IsolatedAsyncioTestCase):
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

            # NOTE: We just dropped database. Let's ensure.
            with self.assertRaises(ConfigurationError):
                schema = await Schema.filter().get()

            # NOTE: Enter DipDup context once again
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

    async def test_reindex_schema_table_migration(self) -> None:
        async with AsyncExitStack() as stack:
            # Arrange
            context.forbid_reindexing = True
            config = DipDupConfig.load([self.path])
            dipdup = await _create_dipdup(config, stack)
            await dipdup._initialize_schema()

            conn = get_connection(None)
            await conn.execute_script(f'UPDATE dipdup_schema SET reindex = "{ReindexingReason.MANUAL.value}"')

            # Act
            with self.assertRaises(ReindexingRequiredError):
                await dipdup._initialize_schema()

            # Assert
            schema = await Schema.filter().get()
            self.assertEqual(ReindexingReason.MANUAL, schema.reindex)

    @skip('FIXME: Exiting stack will kill in-memory database :(')
    async def test_reindex_invalid_schema(self) -> None:
        async with AsyncExitStack() as stack:
            # Arrange
            context.forbid_reindexing = True
            config = DipDupConfig.load([self.path])
            dipdup = await _create_dipdup(config, stack)
            await dipdup._initialize_schema()

            conn = get_connection(None)
            await conn.execute_script('ALTER TABLE dipdup_index DROP COLUMN config_hash')

            # Act
            dipdup = await _create_dipdup(config, stack)
            await dipdup._initialize_schema()
