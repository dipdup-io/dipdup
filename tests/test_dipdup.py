from contextlib import AsyncExitStack
from datetime import datetime
from pathlib import Path

import pytest
from pytz import UTC

from dipdup.config import DipDupConfig
from dipdup.dipdup import DipDup
from dipdup.dipdup import IndexDispatcher
from dipdup.exceptions import ReindexingRequiredError
from dipdup.models import Index
from dipdup.models import IndexStatus
from dipdup.models import IndexType


async def _create_index(hash_: str) -> None:
    await Index.create(
        level=1365000,
        name='hen_mainnet',
        template=None,
        config_hash=hash_,
        created_at=datetime(2021, 10, 8, 18, 43, 35, 744412, tzinfo=UTC),
        template_values={},
        status=IndexStatus.new,
        updated_at=datetime(2021, 10, 8, 18, 43, 35, 744449, tzinfo=UTC),
        type=IndexType.tezos_tzkt_operations,
    )


async def spawn_index(dispatcher: IndexDispatcher, name: str) -> None:
    await dispatcher._ctx._spawn_index(name)
    dispatcher._indexes[name] = dispatcher._ctx._pending_indexes.pop()


class IndexStateTest:
    def __init__(self) -> None:
        name = 'demo_nft_marketplace.yml'
        config_path = Path(__file__).parent / 'configs' / name
        self.config = DipDupConfig.load([config_path])
        self.config.initialize()

        self.new_hash = '98858ec743f2c84ef9505ccefa2235fc6bb9e9b209b14b2028dd4650eaf96756'

    async def test_first_run(self) -> None:
        async with AsyncExitStack() as stack:
            # Arrange
            dipdup = await DipDup.create_dummy(self.config, stack, in_memory=True)
            dispatcher = IndexDispatcher(dipdup._ctx)

            # Act
            await spawn_index(dispatcher, 'hen_mainnet')

            # Assert
            index = await Index.filter().get()
            assert index.config_hash == self.new_hash

    async def test_new_hash(self) -> None:
        async with AsyncExitStack() as stack:
            # Arrange
            dipdup = await DipDup.create_dummy(self.config, stack, in_memory=True)
            dispatcher = IndexDispatcher(dipdup._ctx)
            await _create_index(self.new_hash)

            # Act
            await dispatcher._load_index_state()

            # Assert
            index = await Index.filter().get()
            assert index.config_hash == self.new_hash

    async def test_invalid_hash(self) -> None:
        async with AsyncExitStack() as stack:
            # Arrange
            dipdup = await DipDup.create_dummy(self.config, stack, in_memory=True)
            dispatcher = IndexDispatcher(dipdup._ctx)
            await _create_index('hehehe')

            # Act, Assert
            with pytest.raises(ReindexingRequiredError):
                await dispatcher._load_index_state()
