from contextlib import AsyncExitStack
from pathlib import Path
from typing import AsyncIterator

import pytest

from dipdup.config import DipDupConfig
from dipdup.dipdup import DipDup
from dipdup.enums import ReindexingReason
from dipdup.exceptions import ReindexingRequiredError
from dipdup.models import Schema


@pytest.fixture
async def dummy_dipdup() -> AsyncIterator[DipDup]:
    path = Path(__file__).parent / 'configs' / 'dipdup.yml'
    config = DipDupConfig.load([path])
    async with AsyncExitStack() as stack:
        yield await DipDup.create_dummy(config, stack, in_memory=True)


async def test_reindex_manual(dummy_dipdup: DipDup) -> None:
    # Act
    with pytest.raises(ReindexingRequiredError):
        await dummy_dipdup._ctx.reindex()

    # Assert
    schema = await Schema.filter().get()
    assert schema.reindex == ReindexingReason.manual


async def test_reindex_field(dummy_dipdup: DipDup) -> None:
    await Schema.filter().update(reindex=ReindexingReason.manual)

    # Act
    with pytest.raises(ReindexingRequiredError):
        await dummy_dipdup._initialize_schema()

    # Assert
    schema = await Schema.filter().get()
    assert schema.reindex == ReindexingReason.manual
