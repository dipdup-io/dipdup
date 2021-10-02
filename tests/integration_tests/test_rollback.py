import asyncio
from datetime import datetime
from os.path import dirname, join
from unittest import IsolatedAsyncioTestCase
from unittest.mock import MagicMock, patch

from dipdup.config import DipDupConfig
from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.dipdup import DipDup
from dipdup.models import HeadBlockData
from dipdup.models import Index as State
from dipdup.models import OperationData


def _get_operation(hash_: str, level: int) -> OperationData:
    return OperationData(
        storage={},
        diffs=[],
        type='transaction',
        id=0,
        level=level,
        timestamp=datetime(1970, 1, 1),
        hash=hash_,
        counter=0,
        sender_address='',
        target_address='',
        initiator_address='',
        amount=0,
        status='',
        has_internals=False,
    )


# NOTE: Same level, different hash
old_block = MagicMock(spec=HeadBlockData)
old_block.hash = 'block_a'
old_block.level = 1365001
old_block.timestamp = datetime(2018, 1, 1)
new_block = MagicMock(spec=HeadBlockData)
new_block.hash = 'block_b'
new_block.level = 1365001
new_block.timestamp = datetime(2018, 1, 1)


# NOTE: Emit operations, rollback, emit again, check state
async def datasource_run(self: TzktDatasource):
    await self.emit_operations(
        [
            _get_operation('1', 1365001),
            _get_operation('2', 1365001),
            _get_operation('3', 1365001),
        ],
    )
    await self.emit_rollback(
        from_level=1365001,
        to_level=1365000,
    )
    await self.emit_operations(
        [
            _get_operation('1', 1365001),
            _get_operation('2', 1365001),
            _get_operation('3', 1365001),
        ]
    )

    # NOTE: Assert while Tortoise is still running
    state = await State.filter(name='hen_mainnet').get()
    assert state.level == 1365001, state.level

    raise asyncio.CancelledError


class RollbackTest(IsolatedAsyncioTestCase):
    async def test_rollback_ok(self):
        # Arrange
        config = DipDupConfig.load([join(dirname(__file__), 'hic_et_nunc.yml')])
        config.database.path = ':memory:'
        config.indexes['hen_mainnet'].last_level = config.indexes['hen_mainnet'].first_level + 1
        config.initialize()

        dipdup = DipDup(config)

        # Act
        with patch('dipdup.datasources.tzkt.datasource.TzktDatasource.run', datasource_run):
            await dipdup.run(False, False, False)
