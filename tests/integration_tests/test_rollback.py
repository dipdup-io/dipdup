import asyncio
from datetime import datetime
from functools import partial
from os.path import dirname, join
from types import MethodType
from unittest import IsolatedAsyncioTestCase, skip
from unittest.mock import AsyncMock, MagicMock, patch

from dipdup.config import DipDupConfig
from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.dipdup import DipDup, IndexDispatcher
from dipdup.index import OperationIndex
from dipdup.models import BlockData, HeadBlockData
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


# NOTE: Skip synchronization
async def operation_index_process(self: OperationIndex):
    await self.initialize_state()
    await self._process_queue()


# NOTE: Emit operations, rollback, emit again, check state
async def datasource_run(self: TzktDatasource, index_dispatcher: IndexDispatcher, fail=False):

    old_block = MagicMock(spec=HeadBlockData)
    old_block.hash = 'block_a'
    old_block.level = 1365001
    old_block.timestamp = datetime(2018, 1, 1)
    new_block = MagicMock(spec=HeadBlockData)
    new_block.hash = 'block_b'
    new_block.level = 1365001
    new_block.timestamp = datetime(2018, 1, 1)

    await self.emit_operations(
        [
            _get_operation('1', 1365001),
            _get_operation('2', 1365001),
            _get_operation('3', 1365001),
        ],
    )
    await asyncio.sleep(0.05)

    await self.emit_rollback(
        from_level=1365001,
        to_level=1365000,
    )
    await asyncio.sleep(0.05)

    self.emit_operations(
        [
            _get_operation('1', 1365001),
            _get_operation('2', 1365001),
        ]
        + (
            [
                _get_operation('3', 1365001),
            ]
            if not fail
            else []
        ),
    )
    await asyncio.sleep(0.05)

    index_dispatcher.stop()

    # Assert
    state = await State.filter(name='hen_mainnet').get()
    assert state.level == 1365001


@skip('RuntimeError: Index is synchronized but has no head block data')
class RollbackTest(IsolatedAsyncioTestCase):
    async def test_rollback_ok(self):
        # Arrange
        config = DipDupConfig.load([join(dirname(__file__), 'hic_et_nunc.yml')])
        config.database.path = ':memory:'

        datasource_name, datasource_config = list(config.datasources.items())[0]
        datasource = TzktDatasource('test')
        dipdup = DipDup(config)
        dipdup._datasources[datasource_name] = datasource
        dipdup._datasources_by_config[datasource_config] = datasource

        initial_block = MagicMock(spec=BlockData)
        initial_block.level = 0
        initial_block.hash = 'block_0'

        datasource.on_operations(dipdup._index_dispatcher._on_operations)
        datasource.on_big_maps(dipdup._index_dispatcher._on_big_maps)
        datasource.on_rollback(dipdup._index_dispatcher._on_rollback)

        datasource.run = MethodType(partial(datasource_run, index_dispatcher=dipdup._index_dispatcher), datasource)
        datasource.get_block = AsyncMock(return_value=initial_block)

        # Act
        with patch('dipdup.index.OperationIndex.process', operation_index_process):
            with patch('dipdup.dipdup.INDEX_DISPATCHER_INTERVAL', 0.01):
                await dipdup.run(False, False)

    async def test_rollback_fail(self):
        # Arrange
        config = DipDupConfig.load([join(dirname(__file__), 'hic_et_nunc.yml')])
        config.database.path = ':memory:'

        datasource_name, datasource_config = list(config.datasources.items())[0]
        datasource = TzktDatasource('test')
        dipdup = DipDup(config)
        dipdup._datasources[datasource_name] = datasource
        dipdup._datasources_by_config[datasource_config] = datasource
        dipdup._ctx.reindex = AsyncMock()

        initial_block = MagicMock(spec=BlockData)
        initial_block.level = 0
        initial_block.hash = 'block_0'

        datasource.on_operations(dipdup._index_dispatcher._on_operations)
        datasource.on_big_maps(dipdup._index_dispatcher._on_big_maps)
        datasource.on_rollback(dipdup._index_dispatcher._on_rollback)

        datasource.run = MethodType(partial(datasource_run, index_dispatcher=dipdup._index_dispatcher, fail=True), datasource)
        datasource.get_block = AsyncMock(return_value=initial_block)

        # Act
        with patch('dipdup.index.OperationIndex.process', operation_index_process):
            with patch('dipdup.dipdup.INDEX_DISPATCHER_INTERVAL', 0.01):
                await dipdup.run(False, False)

        dipdup._ctx.reindex.assert_awaited()
