from contextlib import AsyncExitStack
from pathlib import Path
from unittest import IsolatedAsyncioTestCase

from dipdup.config import DipDupConfig
from dipdup.dipdup import DipDup
from dipdup.enums import ReindexingReason
from dipdup.exceptions import ReindexingRequiredError
from dipdup.models import Schema


class ReindexingTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.path = Path(__file__).parent / 'configs' / 'dipdup.yml'

    async def test_reindex_manual(self) -> None:
        async with AsyncExitStack() as stack:
            # Arrange
            config = DipDupConfig.load([self.path])
            dipdup = await DipDup.create_dummy(config, stack, in_memory=True)

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
            dipdup = await DipDup.create_dummy(config, stack, in_memory=True)

            await Schema.filter().update(reindex=ReindexingReason.manual)

            # Act
            with self.assertRaises(ReindexingRequiredError):
                await dipdup._initialize_schema()

            # Assert
            schema = await Schema.filter().get()
            self.assertEqual(ReindexingReason.manual, schema.reindex)
