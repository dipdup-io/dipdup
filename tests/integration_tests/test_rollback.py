import asyncio
from datetime import datetime
from functools import partial
from os.path import dirname, join
from types import MethodType
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

from dipdup.config import DipDupConfig
from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.dipdup import DipDup, IndexDispatcher
from dipdup.index import OperationIndex
from dipdup.models import BlockData, OperationData, State


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
        amount=0,
        status='',
        has_internals=False,
    )


# NOTE: Skip synchronization
async def operation_index_process(self: OperationIndex):
    await self._process_queue()


# NOTE: Emit operations, rollback, emit again, check state
async def datasource_run(self: TzktDatasource, index_dispatcher: IndexDispatcher, fail=False):

    self._block = MagicMock(spec=BlockData)
    self._block.hash = 'block_a'
    self._block.level = 1365000

    self.emit(
        "operations",
        [
            _get_operation('1', 1365001),
            _get_operation('2', 1365001),
            _get_operation('3', 1365001),
        ],
        'block_b',
    )
    await asyncio.sleep(0.05)

    self.emit(
        "rollback",
        from_level=1365001,
        to_level=1365000,
    )
    await asyncio.sleep(0.05)

    self.emit(
        "operations",
        [
            _get_operation('1', 1365001),
            _get_operation('2', 1365001),
            _get_operation('3', 1365001),
        ]
        + ([_get_operation('4', 1365001)] if fail else []),
        'block_c',
    )
    await asyncio.sleep(0.05)

    index_dispatcher.stop()

    # Assert
    state = await State.filter(index_name='hen_mainnet').get()
    assert state.level == 1365001
    state.hash == 'block_c'


class RollbackTest(IsolatedAsyncioTestCase):
    async def test_rollback_ok(self):
        # Arrange
        config = DipDupConfig.load([join(dirname(__file__), 'hic_et_nunc.yml')])
        config.database.path = ':memory:'

        datasource_name, datasource_config = list(config.datasources.items())[0]
        datasource = TzktDatasource('test', False)
        dipdup = DipDup(config)
        dipdup._datasources[datasource_name] = datasource
        dipdup._datasources_by_config[datasource_config] = datasource

        datasource.on('operations', dipdup._index_dispatcher.dispatch_operations)
        datasource.on('big_maps', dipdup._index_dispatcher.dispatch_big_maps)
        datasource.on('rollback', partial(dipdup._index_dispatcher._rollback, datasource_name='tzkt_mainnet'))

        datasource.run = MethodType(partial(datasource_run, index_dispatcher=dipdup._index_dispatcher), datasource)
        datasource.get_block = AsyncMock(return_value={'level': 0, 'hash': '0'})

        # Act
        with patch('dipdup.index.OperationIndex.process', operation_index_process):
            with patch('dipdup.dipdup.INDEX_DISPATCHER_INTERVAL', 0.01):
                await dipdup.run(False, False)

    async def test_rollback_fail(self):
        # Arrange
        config = DipDupConfig.load([join(dirname(__file__), 'hic_et_nunc.yml')])
        config.database.path = ':memory:'

        datasource_name, datasource_config = list(config.datasources.items())[0]
        datasource = TzktDatasource('test', False)
        dipdup = DipDup(config)
        dipdup._datasources[datasource_name] = datasource
        dipdup._datasources_by_config[datasource_config] = datasource
        dipdup._ctx.reindex = AsyncMock()

        datasource.on('operations', dipdup._index_dispatcher.dispatch_operations)
        datasource.on('big_maps', dipdup._index_dispatcher.dispatch_big_maps)
        datasource.on('rollback', partial(dipdup._index_dispatcher._rollback, datasource_name='tzkt_mainnet'))

        datasource.run = MethodType(partial(datasource_run, index_dispatcher=dipdup._index_dispatcher, fail=True), datasource)
        datasource.get_block = AsyncMock(return_value={'level': 0, 'hash': '0'})

        # Act
        with patch('dipdup.index.OperationIndex.process', operation_index_process):
            with patch('dipdup.dipdup.INDEX_DISPATCHER_INTERVAL', 0.01):
                await dipdup.run(False, False)

        dipdup._ctx.reindex.assert_awaited()
