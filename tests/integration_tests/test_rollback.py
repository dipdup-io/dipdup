import asyncio
from datetime import datetime
from os.path import dirname, join
from typing import Tuple
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

from dipdup.config import DipDupConfig
from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.dipdup import DipDup
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

initial_level = 1365000

exact_operations = (
    _get_operation('1', 1365001),
    _get_operation('2', 1365001),
    _get_operation('3', 1365001),
)

less_operations = (
    _get_operation('1', 1365001),
    _get_operation('2', 1365001),
)

more_operations = (
    _get_operation('1', 1365001),
    _get_operation('2', 1365001),
    _get_operation('3', 1365001),
    _get_operation('4', 1365001),
)


async def check_level(level: int) -> None:
    state = await State.filter(name='hen_mainnet').get()
    assert state.level == level, state.level


async def emit_messages(
    self: TzktDatasource,
    old_block: Tuple[OperationData, ...],
    new_block: Tuple[OperationData, ...],
    level: int,
):
    await self.emit_operations(old_block)
    await self.emit_rollback(
        from_level=1365001,
        to_level=1365001 - level,
    )
    await self.emit_operations(new_block)

    raise asyncio.CancelledError


async def datasource_run_exact(self: TzktDatasource):
    await emit_messages(self, exact_operations, exact_operations, 1)
    await check_level(initial_level + 1)


class RollbackTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.config = DipDupConfig.load([join(dirname(__file__), 'hic_et_nunc.yml')])
        self.config.database.path = ':memory:'
        self.config.indexes['hen_mainnet'].last_level = self.config.indexes['hen_mainnet'].first_level + 1
        self.config.initialize()
        self.dipdup = DipDup(self.config)


    async def test_rollback_ok(self):
        with patch('dipdup.datasources.tzkt.datasource.TzktDatasource.run', datasource_run_exact):
            await self.dipdup.run(False, False, False)
