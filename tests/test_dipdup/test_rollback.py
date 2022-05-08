from unittest import IsolatedAsyncioTestCase
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
from dipdup.index import BigMapIndex
from dipdup.index import HeadIndex
from dipdup.index import OperationIndex


def _get_index_dispatcher() -> IndexDispatcher:
    return IndexDispatcher(
        ctx=Mock(spec=DipDupContext),
    )


def _get_operation_index(level: int) -> OperationIndex:
    config = OperationIndexConfig(
        kind='operation',
        datasource='',
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
    config.name = 'operation'
    index = OperationIndex(
        ctx=Mock(spec=DipDupContext),
        datasource=Mock(spec=TzktDatasource),
        config=config,
    )
    index._state = models.Index(level=level)
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


class RollbackTest(IsolatedAsyncioTestCase):
    async def test_forward_rollback(self) -> None:
        from_level, to_level = 20, 30
        dispatcher = _get_index_dispatcher()
        with self.assertRaises(RuntimeError):
            await dispatcher._on_rollback(
                datasource=Mock(spec=TzktDatasource),
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
            from_level=from_level,
            to_level=to_level,
        )
        dispatcher._ctx.fire_hook.assert_awaited_with(  # type: ignore
            'on_rollback',
            datasource=head_index.datasource,
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
            from_level=from_level,
            to_level=to_level,
        )
        dispatcher._ctx.fire_hook.assert_awaited_with(  # type: ignore
            'on_rollback',
            datasource=operation_index.datasource,
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
            from_level=from_level,
            to_level=to_level,
        )
        dispatcher._ctx.fire_hook.assert_awaited_with(  # type: ignore
            'on_rollback',
            datasource=big_map_index.datasource,
            from_level=from_level,
            to_level=to_level,
        )
        self.assertEqual(0, len(big_map_index._queue))
