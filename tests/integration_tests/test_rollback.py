import asyncio
import logging
from datetime import datetime
from os.path import dirname, join
from types import MethodType
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

from dipdup.config import DipDupConfig
from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.dipdup import DipDup
from dipdup.index import OperationIndex
from dipdup.models import OperationData

logging.basicConfig()
logging.getLogger().setLevel(0)


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


# NOTE: Emit operations, rollback, emit again
async def datasource_run(self: TzktDatasource):
    await asyncio.sleep(1)
    print('run datasource')
    self.emit(
        "operations",
        [
            _get_operation('1', 1365001),
            _get_operation('2', 1365001),
            _get_operation('3', 1365001),
        ],
    )

    self.emit("self, rollback", 2, 1)
    await asyncio.sleep(1)

    self.emit(
        "operations",
        [
            _get_operation('1', 1365001),
            _get_operation('2', 1365001),
            _get_operation('3', 1365001),
        ],
    )
    await asyncio.sleep(1)
    raise KeyboardInterrupt


class RollbackTest(IsolatedAsyncioTestCase):
    async def test_rollback_ok(self):
        # Arrange
        config = DipDupConfig.load([join(dirname(__file__), 'hic_et_nunc.yml')])
        datasource_name, datasource_config = list(config.datasources.items())[0]
        datasource = TzktDatasource('', False)
        datasource.run = MethodType(datasource_run, datasource)
        datasource.get_block = AsyncMock(return_value={'level': 0, 'hash': '0'})
        dipdup = DipDup(config)
        dipdup._datasources[datasource_name] = datasource
        dipdup._datasources_by_config[datasource_config] = datasource

        # Act
        with patch('dipdup.index.OperationIndex.process', operation_index_process):
            await dipdup.run(False, False)

        # process operations
        # rollback

    async def test_rollback_fail(self):
        ...
