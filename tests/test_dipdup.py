from contextlib import AsyncExitStack
from datetime import datetime
from pathlib import Path

import pytest
from pytz import UTC

from dipdup.config import DipDupConfig
from dipdup.config import SqliteDatabaseConfig
from dipdup.exceptions import ReindexingRequiredError
from dipdup.models import Index
from dipdup.models import IndexStatus
from dipdup.models import IndexType
from dipdup.test import create_dummy_dipdup
from dipdup.test import spawn_index


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


class IndexStateTest:
    def __init__(self) -> None:
        name = 'demo_nft_marketplace.yml'
        config_path = Path(__file__).parent / 'configs' / name
        self.config = DipDupConfig.load([config_path])
        self.config.database = SqliteDatabaseConfig(kind='sqlite')
        self.config.advanced.rollback_depth = 2
        self.config.initialize()

        self.new_hash = '98858ec743f2c84ef9505ccefa2235fc6bb9e9b209b14b2028dd4650eaf96756'

    async def test_first_run(self) -> None:
        async with AsyncExitStack() as stack:
            # Arrange
            dipdup = await create_dummy_dipdup(self.config, stack)

            # Act
            await spawn_index(dipdup, 'hen_mainnet')

            # Assert
            index = await Index.filter().get()
            assert index.config_hash == self.new_hash

    async def test_new_hash(self) -> None:
        async with AsyncExitStack() as stack:
            # Arrange
            dipdup = await create_dummy_dipdup(self.config, stack)

            await _create_index(self.new_hash)

            # Act
            await dipdup._index_dispatcher._load_index_state()

            # Assert
            index = await Index.filter().get()
            assert index.config_hash == self.new_hash

    async def test_invalid_hash(self) -> None:
        async with AsyncExitStack() as stack:
            # Arrange
            dipdup = await create_dummy_dipdup(self.config, stack)

            await _create_index('hehehe')

            # Act, Assert
            with pytest.raises(ReindexingRequiredError):
                await dipdup._index_dispatcher._load_index_state()

    async def test_metrics(self) -> None:
        async with AsyncExitStack() as stack:
            # Arrange
            dipdup = await create_dummy_dipdup(self.config, stack)
            dispatcher = dipdup._index_dispatcher

            # Act
            await dispatcher._update_metrics()
            await dispatcher._update_prometheus()
