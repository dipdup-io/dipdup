from contextlib import AsyncExitStack
from os.path import dirname, join
from unittest import IsolatedAsyncioTestCase

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
    await dipdup._set_up_database(stack)
    await dipdup._set_up_hooks()
    await dipdup._initialize_schema()
    return dipdup


class ReindexingTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.path = join(dirname(__file__), 'dipdup.yml')

    async def test_reindex_manual(self):
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

    async def test_reindex_field(self):
        async with AsyncExitStack() as stack:
            # Arrange
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
