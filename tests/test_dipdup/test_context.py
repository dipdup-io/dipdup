from contextlib import AsyncExitStack
from pathlib import Path
from unittest import IsolatedAsyncioTestCase

from dipdup.config import DipDupConfig
from dipdup.config import SqliteDatabaseConfig
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
    await dipdup._set_up_hooks(set())
    await dipdup._initialize_schema()
    return dipdup


class ReindexingTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.path = Path(__file__).parent / 'dipdup.yml'

    async def test_reindex_manual(self) -> None:
        async with AsyncExitStack() as stack:
            # Arrange
            config = DipDupConfig.load([self.path])
            dipdup = await _create_dipdup(config, stack)

            # Act
            with self.assertRaises(ReindexingRequiredError):
                await dipdup._ctx.reindex()

            # Assert
            schema = await Schema.filter().get()
            self.assertEqual(ReindexingReason.manual, schema.reindex)

    async def test_reindex_field(self) -> None:
        async with AsyncExitStack() as stack:
            # Arrange
            config = DipDupConfig.load([self.path])
            dipdup = await _create_dipdup(config, stack)

            await Schema.filter().update(reindex=ReindexingReason.manual)

            # Act
            with self.assertRaises(ReindexingRequiredError):
                await dipdup._initialize_schema()

            # Assert
            schema = await Schema.filter().get()
            self.assertEqual(ReindexingReason.manual, schema.reindex)
