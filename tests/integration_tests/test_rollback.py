import asyncio
from contextlib import ExitStack, contextmanager
from datetime import datetime
from os.path import dirname, join
from typing import Generator, Tuple
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock, patch

from dipdup.config import DipDupConfig
from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.dipdup import DipDup
from dipdup.models import HeadBlockData
from dipdup.models import Index as State
from dipdup.models import OperationData

# import logging
# logging.basicConfig(level=logging.INFO)


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
next_level = initial_level + 1

exact_operations = (
    _get_operation('1', next_level),
    _get_operation('2', next_level),
    _get_operation('3', next_level),
)

less_operations = (
    _get_operation('1', next_level),
    _get_operation('2', next_level),
)

more_operations = (
    _get_operation('1', next_level),
    _get_operation('2', next_level),
    _get_operation('3', next_level),
    _get_operation('4', next_level),
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
        from_level=next_level,
        to_level=next_level - level,
    )
    await self.emit_operations(new_block)

    for _ in range(10):
        await asyncio.sleep(0.1)

    raise asyncio.CancelledError


async def datasource_run_exact(self: TzktDatasource):
    await emit_messages(self, exact_operations, exact_operations, 1)
    await check_level(initial_level + 1)


async def datasource_run_more(self: TzktDatasource):
    await emit_messages(self, exact_operations, more_operations, 1)
    await check_level(initial_level + 1)


async def datasource_run_less(self: TzktDatasource):
    await emit_messages(self, exact_operations, less_operations, 1)
    await check_level(initial_level + 1)


async def datasource_run_zero(self: TzktDatasource):
    await emit_messages(self, (), (exact_operations), 0)
    await check_level(initial_level + 1)


async def datasource_run_deep(self: TzktDatasource):
    await emit_messages(self, (exact_operations), (), 1337)
    await check_level(initial_level + 1)


head = Mock(spec=HeadBlockData)
head.level = initial_level


@contextmanager
def patch_dipdup(datasource_run) -> Generator:
    with ExitStack() as stack:
        stack.enter_context(patch('dipdup.index.OperationIndex._synchronize', AsyncMock()))
        stack.enter_context(patch('dipdup.datasources.tzkt.datasource.TzktDatasource.run', datasource_run))
        stack.enter_context(patch('dipdup.context.DipDupContext.reindex', AsyncMock()))
        stack.enter_context(patch('dipdup.datasources.tzkt.datasource.TzktDatasource.get_head_block', AsyncMock(return_value=head)))
        yield


def get_dipdup() -> DipDup:
    config = DipDupConfig.load([join(dirname(__file__), 'hic_et_nunc.yml')])
    config.database.path = ':memory:'  # type: ignore
    config.indexes['hen_mainnet'].last_level = 0  # type: ignore
    config.initialize()
    return DipDup(config)


class RollbackTest(IsolatedAsyncioTestCase):
    async def test_rollback_exact(self):
        with patch_dipdup(datasource_run_exact):
            dipdup = get_dipdup()
            await dipdup.run(False, False, False)

            assert dipdup._ctx.reindex.call_count == 0

    async def test_rollback_more(self):
        with patch_dipdup(datasource_run_more):
            dipdup = get_dipdup()
            await dipdup.run(False, False, False)

            assert dipdup._ctx.reindex.call_count == 0

    async def test_rollback_less(self):
        with patch_dipdup(datasource_run_less):
            dipdup = get_dipdup()
            await dipdup.run(False, False, False)

            assert dipdup._ctx.reindex.call_count == 1

    async def test_rollback_zero(self):
        with patch_dipdup(datasource_run_zero):
            dipdup = get_dipdup()
            await dipdup.run(False, False, False)

            assert dipdup._ctx.reindex.call_count == 0

    async def test_rollback_deep(self):
        with patch_dipdup(datasource_run_deep):
            dipdup = get_dipdup()
            await dipdup.run(False, False, False)

            assert dipdup._ctx.reindex.call_count == 1
