import asyncio
from abc import abstractmethod
from collections import defaultdict
from enum import Enum
from logging import Logger
from typing import Awaitable, DefaultDict, List, Protocol

from pyee import AsyncIOEventEmitter  # type: ignore

from dipdup.config import HTTPConfig
from dipdup.http import HTTPGateway
from dipdup.models import BigMapData, HeadBlockData, OperationData


class DatasourceEventEmitter(AsyncIOEventEmitter):
    """This class changes behavior of emit method to block execution until previous level emit callbacks are done"""

    def __init__(self) -> None:
        super(AsyncIOEventEmitter, self).__init__()
        self._prefix = 'emit_'
        self._tasks: DefaultDict[int, List[asyncio.Task]] = defaultdict(list)

    def _level_has_pending_tasks(self, level: int) -> bool:
        for task_level in self._tasks:
            if task_level < level and filter(lambda t: not t.done(), self._tasks[task_level]):
                return True
        return False

    async def level_emit(self, level: int, event, *args, **kwargs) -> None:
        timeout, sleep = 60, 0.5
        for _ in range(int(timeout / sleep)):
            if self._level_has_pending_tasks(level):
                await asyncio.sleep(sleep)
            else:
                kwargs['_level'] = level
                super().emit(event, *args, **kwargs)
                break
        else:
            raise RuntimeError(f'Levels lower than {level} are still processing after {timeout} seconds')

    def _emit_run(self, f, args, kwargs) -> None:
        level = kwargs.pop('_level', 0)
        if level:
            task = asyncio.create_task(f(*args, **kwargs), name=f'{self._prefix}_{level}')
            self._tasks[level].append(task)
        else:
            task = asyncio.create_task(f(*args, **kwargs))

        def _callback(f: asyncio.Task):
            if f.cancelled():
                return

            exc = f.exception()
            if exc:
                # TODO: Keep exception
                self.emit('error', exc)

        task.add_done_callback(_callback)


class EventType(Enum):
    operations = 'operatitions'
    big_maps = 'big_maps'
    rollback = 'rollback'
    head = 'head'


class OperationsCallback(Protocol):
    def __call__(self, datasource: 'IndexDatasource', operations: List[OperationData], block: HeadBlockData) -> Awaitable[None]:
        ...


class BigMapsCallback(Protocol):
    def __call__(self, datasource: 'IndexDatasource', big_maps: List[BigMapData], block: HeadBlockData) -> Awaitable[None]:
        ...


class RollbackCallback(Protocol):
    def __call__(self, datasource: 'IndexDatasource', from_level: int, to_level: int) -> Awaitable[None]:
        ...


class HeadCallback(Protocol):
    def __call__(self, datasource: 'IndexDatasource', block: HeadBlockData) -> Awaitable[None]:
        ...


class Datasource(HTTPGateway):
    _logger: Logger

    @abstractmethod
    async def run(self) -> None:
        ...


class IndexDatasource(Datasource, DatasourceEventEmitter):
    def __init__(self, url: str, http_config: HTTPConfig) -> None:
        HTTPGateway.__init__(self, url, http_config)
        DatasourceEventEmitter.__init__(self)

    def on(self, event, f=None) -> None:
        raise RuntimeError('Do not use `on` directly')

    def emit(self, event: str, *args, **kwargs) -> None:
        if event not in ('new_listener', 'error'):
            raise RuntimeError('Do not use `emit` directly')
        super().emit(event, *args, **kwargs)

    def on_head(self, fn: HeadCallback) -> None:
        super().on(EventType.head, fn)

    def on_operations(self, fn: OperationsCallback) -> None:
        super().on(EventType.operations, fn)

    def on_big_maps(self, fn: BigMapsCallback) -> None:
        super().on(EventType.big_maps, fn)

    def on_rollback(self, fn: RollbackCallback) -> None:
        super().on(EventType.rollback, fn)

    async def emit_head(self, block: HeadBlockData) -> None:
        await self.level_emit(block.level, EventType.head, datasource=self, block=block)

    async def emit_operations(self, operations: List[OperationData], block: HeadBlockData) -> None:
        if not operations:
            return
        await self.level_emit(operations[0].level, EventType.operations, datasource=self, operations=operations, block=block)

    async def emit_big_maps(self, big_maps: List[BigMapData], block: HeadBlockData) -> None:
        if not big_maps:
            return
        await self.level_emit(big_maps[0].level, EventType.big_maps, datasource=self, big_maps=big_maps, block=block)

    def emit_rollback(self, from_level: int, to_level: int) -> None:
        super().emit(EventType.rollback, datasource=self, from_level=from_level, to_level=to_level)
