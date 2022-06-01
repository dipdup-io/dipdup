from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import Mock

from dipdup import models
from dipdup.config import BigMapHandlerConfig
from dipdup.config import BigMapIndexConfig
from dipdup.config import ContractConfig
from dipdup.config import HeadHandlerConfig
from dipdup.config import HeadIndexConfig
from dipdup.config import OperationHandlerConfig
from dipdup.config import OperationHandlerTransactionPatternConfig
from dipdup.config import OperationIndexConfig
from dipdup.context import DipDupContext
from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.dipdup import IndexDispatcher
from dipdup.enums import MessageType
from dipdup.enums import ReindexingReason
from dipdup.index import BigMapIndex
from dipdup.index import HeadIndex
from dipdup.index import OperationIndex
from dipdup.index import OperationSubgroup
from dipdup.utils.database import tortoise_wrapper


def _get_index_dispatcher() -> IndexDispatcher:
    index_dispatcher = IndexDispatcher(
        ctx=MagicMock(spec=DipDupContext),
    )
    index_dispatcher._ctx.reindex = AsyncMock()  # type: ignore
    index_dispatcher._ctx.config = AsyncMock()  # type: ignore
    return index_dispatcher


def _get_operation_index(level: int) -> OperationIndex:
    config = OperationIndexConfig(
        kind='operation',
        datasource='',
        contracts=[
            ContractConfig(address='KT1000000000000000000000000000000000'),
        ],
        handlers=(
            OperationHandlerConfig(
                callback='',
                pattern=(
                    OperationHandlerTransactionPatternConfig(
                        type='transaction',
                        destination=ContractConfig(address='KT1000000000000000000000000000000000'),
                        entrypoint='yes',
                    ),
                ),
            ),
        ),
    )
    config.handlers[0].pattern[0].parameter_type_cls = MagicMock()  # type: ignore
    config.handlers[0].pattern[0].storage_type_cls = MagicMock()
    config.name = 'operation'
    index = OperationIndex(
        ctx=Mock(spec=DipDupContext),
        datasource=Mock(spec=TzktDatasource),
        config=config,
    )
    index._state = models.Index(level=level)
    index._state.save = AsyncMock()  # type: ignore
    index._call_matched_handler = AsyncMock()  # type: ignore
    index._ctx.reindex = AsyncMock()  # type: ignore
    index._ctx.config = MagicMock()

    return index


def _get_big_map_index(level: int) -> BigMapIndex:
    config = BigMapIndexConfig(
        kind='big_map',
        datasource='',
        handlers=(
            BigMapHandlerConfig(
                contract='yes',
                path='yes',
                callback='',
            ),
        ),
    )
    config.name = 'big_map'
    index = BigMapIndex(
        ctx=Mock(spec=DipDupContext),
        datasource=Mock(spec=TzktDatasource),
        config=config,
    )
    index._state = models.Index(level=level)
    return index


def _get_head_index(level: int) -> HeadIndex:
    config = HeadIndexConfig(
        kind='head',
        datasource='',
        handlers=(
            HeadHandlerConfig(
                callback='',
            ),
        ),
    )
    config.name = 'head'
    index = HeadIndex(
        ctx=Mock(spec=DipDupContext),
        datasource=Mock(spec=TzktDatasource),
        config=config,
    )
    index._state = models.Index(level=level)
    return index


def _get_subgroup(level: int, id_: int = 0, matched: int = 0) -> OperationSubgroup:
    op = MagicMock(spec=models.OperationData)
    op.type = 'transaction'
    op.level = level
    op.hash = id_
    op.counter = id_
    op.entrypoint = 'yes' if matched else 'no'
    op.target_address = 'KT1000000000000000000000000000000000'
    op.diffs = []
    op.storage = {}

    return OperationSubgroup(
        operations=(op,),
        hash=str(id_),
        counter=id_,
        entrypoints={'yes' if matched else 'no'},  # type: ignore
    )


class RollbackTest(IsolatedAsyncioTestCase):
    async def test_forward_rollback(self) -> None:
        from_level, to_level = 20, 30
        dispatcher = _get_index_dispatcher()
        with self.assertRaises(RuntimeError):
            await dispatcher._on_rollback(
                datasource=Mock(spec=TzktDatasource),
                type_=MessageType.operation,
                from_level=from_level,
                to_level=to_level,
            )

    async def test_not_affected_by_level(self) -> None:
        index_level, from_level, to_level = 10, 20, 15
        dispatcher = _get_index_dispatcher()
        operation_index = _get_operation_index(level=index_level)
        dispatcher._indexes = {
            'operation': operation_index,
        }
        await dispatcher._on_rollback(
            datasource=operation_index.datasource,
            type_=MessageType.operation,
            from_level=from_level,
            to_level=to_level,
        )
        self.assertIsNone(operation_index._next_head_level)
        dispatcher._ctx.fire_hook.assert_not_awaited()  # type: ignore
        self.assertEqual(0, len(operation_index._queue))

    async def test_not_affected_by_datasource(self) -> None:
        other_datasource = Mock(spec=TzktDatasource)
        index_level, from_level, to_level = 20, 20, 15
        dispatcher = _get_index_dispatcher()
        operation_index = _get_operation_index(level=index_level)
        dispatcher._indexes = {
            'operation': operation_index,
        }
        await dispatcher._on_rollback(
            datasource=other_datasource,
            type_=MessageType.operation,
            from_level=from_level,
            to_level=to_level,
        )
        self.assertIsNone(operation_index._next_head_level)
        dispatcher._ctx.fire_hook.assert_not_awaited()  # type: ignore
        self.assertEqual(0, len(operation_index._queue))

    async def test_not_affected_by_type(self) -> None:
        index_level, from_level, to_level = 20, 20, 15
        dispatcher = _get_index_dispatcher()
        operation_index = _get_operation_index(level=index_level)
        dispatcher._indexes = {
            'operation': operation_index,
        }
        await dispatcher._on_rollback(
            datasource=operation_index.datasource,
            type_=MessageType.head,
            from_level=from_level,
            to_level=to_level,
        )
        self.assertIsNone(operation_index._next_head_level)
        dispatcher._ctx.fire_hook.assert_not_awaited()  # type: ignore
        self.assertEqual(0, len(operation_index._queue))

    async def test_unprocessed_head(self) -> None:
        index_level, from_level, to_level = 20, 20, 15
        dispatcher = _get_index_dispatcher()
        head_index = _get_head_index(level=index_level)
        dispatcher._indexes = {
            'head': head_index,
        }
        await dispatcher._on_rollback(
            datasource=head_index.datasource,
            type_=MessageType.head,
            from_level=from_level,
            to_level=to_level,
        )
        dispatcher._ctx.fire_hook.assert_awaited_with(  # type: ignore
            'on_index_rollback',
            index=head_index,
            from_level=from_level,
            to_level=to_level,
        )
        self.assertEqual(0, len(head_index._queue))

    async def test_unprocessed(self) -> None:
        index_level, from_level, to_level = 20, 20, 15
        dispatcher = _get_index_dispatcher()
        operation_index = _get_operation_index(level=index_level)
        dispatcher._indexes = {
            'operation': operation_index,
        }
        await dispatcher._on_rollback(
            datasource=operation_index.datasource,
            type_=MessageType.operation,
            from_level=from_level,
            to_level=to_level,
        )
        dispatcher._ctx.fire_hook.assert_awaited_with(  # type: ignore
            'on_index_rollback',
            index=operation_index,
            from_level=from_level,
            to_level=to_level,
        )
        self.assertEqual(0, len(operation_index._queue))

    async def test_single_level_supported(self) -> None:
        index_level, from_level, to_level = 20, 20, 19
        dispatcher = _get_index_dispatcher()
        operation_index = _get_operation_index(level=index_level)
        dispatcher._indexes = {
            'operation': operation_index,
        }
        await dispatcher._on_rollback(
            datasource=operation_index.datasource,
            type_=MessageType.operation,
            from_level=from_level,
            to_level=to_level,
        )
        dispatcher._ctx.fire_hook.assert_not_awaited()  # type: ignore
        self.assertEqual(1, len(operation_index._queue))
        self.assertEqual(20, operation_index._queue[0].from_level)  # type: ignore

    async def test_single_level_not_supported(self) -> None:
        index_level, from_level, to_level = 20, 20, 19
        dispatcher = _get_index_dispatcher()
        big_map_index = _get_big_map_index(level=index_level)
        dispatcher._indexes = {
            'big_map': big_map_index,
        }
        await dispatcher._on_rollback(
            datasource=big_map_index.datasource,
            type_=MessageType.big_map,
            from_level=from_level,
            to_level=to_level,
        )
        dispatcher._ctx.fire_hook.assert_awaited_with(  # type: ignore
            'on_index_rollback',
            index=big_map_index,
            from_level=from_level,
            to_level=to_level,
        )
        self.assertEqual(0, len(big_map_index._queue))

    async def test_single_level_new_head_equal(self) -> None:
        index_level, from_level, to_level = 20, 20, 19
        operation_index = _get_operation_index(level=index_level)
        dispatcher = _get_index_dispatcher()
        dispatcher._indexes = {
            'operation': operation_index,
        }

        async with tortoise_wrapper('sqlite://:memory:'):
            await operation_index._process_level_operations(
                (
                    _get_subgroup(level=index_level, id_=0, matched=True),
                    _get_subgroup(level=index_level, id_=1, matched=True),
                    _get_subgroup(level=index_level, id_=2, matched=False),
                )
            )
            assert operation_index._head_hashes == {'0': True, '1': True, '2': False}

            await dispatcher._on_rollback(
                datasource=operation_index.datasource,
                type_=MessageType.operation,
                from_level=from_level,
                to_level=to_level,
            )
            assert len(operation_index._queue) == 1

            await operation_index._process_queue()
            assert operation_index._next_head_level == from_level

            await operation_index._process_level_operations(
                (
                    _get_subgroup(level=index_level, id_=0, matched=True),
                    _get_subgroup(level=index_level, id_=1, matched=True),
                    _get_subgroup(level=index_level, id_=2, matched=False),
                )
            )
            await operation_index._process_queue()
            assert operation_index._next_head_level is None
            assert operation_index.state.level == from_level
            operation_index._ctx.reindex.assert_not_awaited()
            assert operation_index._call_matched_handler.await_count == 2

    async def test_single_level_new_head_less(self) -> None:
        index_level, from_level, to_level = 20, 20, 19
        operation_index = _get_operation_index(level=index_level)
        dispatcher = _get_index_dispatcher()
        dispatcher._indexes = {
            'operation': operation_index,
        }

        async with tortoise_wrapper('sqlite://:memory:'):
            await operation_index._process_level_operations(
                (
                    _get_subgroup(level=index_level, id_=0, matched=True),
                    _get_subgroup(level=index_level, id_=1, matched=True),
                    _get_subgroup(level=index_level, id_=2, matched=False),
                )
            )
            assert operation_index._head_hashes == {'0': True, '1': True, '2': False}

            await dispatcher._on_rollback(
                datasource=operation_index.datasource,
                type_=MessageType.operation,
                from_level=from_level,
                to_level=to_level,
            )
            assert len(operation_index._queue) == 1

            await operation_index._process_queue()
            assert operation_index._next_head_level == from_level

            await operation_index._process_level_operations(
                (
                    _get_subgroup(level=index_level, id_=0, matched=True),
                    _get_subgroup(level=index_level, id_=2, matched=False),
                )
            )
            await operation_index._process_queue()
            assert operation_index._next_head_level is None
            assert operation_index.state.level == from_level

            operation_index._ctx.fire_hook.assert_awaited_with(
                'on_index_rollback',
                index=operation_index,
                from_level=from_level,
                to_level=to_level,
            )
            assert operation_index._call_matched_handler.await_count == 2

    async def test_single_level_new_head_less_not_matched(self) -> None:
        index_level, from_level, to_level = 20, 20, 19
        operation_index = _get_operation_index(level=index_level)
        dispatcher = _get_index_dispatcher()
        dispatcher._indexes = {
            'operation': operation_index,
        }

        async with tortoise_wrapper('sqlite://:memory:'):
            await operation_index._process_level_operations(
                (
                    _get_subgroup(level=index_level, id_=0, matched=True),
                    _get_subgroup(level=index_level, id_=1, matched=True),
                    _get_subgroup(level=index_level, id_=2, matched=False),
                )
            )
            assert operation_index._head_hashes == {'0': True, '1': True, '2': False}

            await dispatcher._on_rollback(
                datasource=operation_index.datasource,
                type_=MessageType.operation,
                from_level=from_level,
                to_level=to_level,
            )
            assert len(operation_index._queue) == 1

            await operation_index._process_queue()
            assert operation_index._next_head_level == from_level

            await operation_index._process_level_operations(
                (
                    _get_subgroup(level=index_level, id_=0, matched=True),
                    _get_subgroup(level=index_level, id_=1, matched=True),
                )
            )
            await operation_index._process_queue()
            assert operation_index._next_head_level is None
            assert operation_index.state.level == from_level
            operation_index._ctx.reindex.assert_not_awaited()
            assert operation_index._call_matched_handler.await_count == 2

    async def test_single_level_new_head_more(self) -> None:
        index_level, from_level, to_level = 20, 20, 19
        operation_index = _get_operation_index(level=index_level)
        dispatcher = _get_index_dispatcher()
        dispatcher._indexes = {
            'operation': operation_index,
        }

        async with tortoise_wrapper('sqlite://:memory:'):
            await operation_index._process_level_operations(
                (
                    _get_subgroup(level=index_level, id_=0, matched=True),
                    _get_subgroup(level=index_level, id_=1, matched=True),
                    _get_subgroup(level=index_level, id_=2, matched=False),
                )
            )
            assert operation_index._head_hashes == {'0': True, '1': True, '2': False}

            await dispatcher._on_rollback(
                datasource=operation_index.datasource,
                type_=MessageType.operation,
                from_level=from_level,
                to_level=to_level,
            )
            assert len(operation_index._queue) == 1

            await operation_index._process_queue()
            assert operation_index._next_head_level == from_level

            await operation_index._process_level_operations(
                (
                    _get_subgroup(level=index_level, id_=0, matched=True),
                    _get_subgroup(level=index_level, id_=1, matched=True),
                    _get_subgroup(level=index_level, id_=2, matched=False),
                    _get_subgroup(level=index_level, id_=3, matched=True),
                )
            )
            await operation_index._process_queue()

            assert operation_index._next_head_level is None
            assert operation_index.state.level == from_level
            operation_index._ctx.reindex.assert_not_awaited()
            assert operation_index._call_matched_handler.await_count == 3
