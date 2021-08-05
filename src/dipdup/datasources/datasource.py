from abc import abstractmethod
from enum import Enum
from logging import Logger
from typing import Awaitable, List, Optional, Protocol

from pyee import AsyncIOEventEmitter  # type: ignore

from dipdup.config import HTTPConfig
from dipdup.http import HTTPGateway
from dipdup.models import BigMapData, HeadBlockData, OperationData


class EventType(Enum):
    operations = 'operatitions'
    big_maps = 'big_maps'
    rollback = 'rollback'
    head = 'head'


class OperationsCallback(Protocol):
    def __call__(self, datasource: 'IndexDatasource', operations: List[OperationData], block: HeadBlockData) -> Awaitable[None]:
        ...


class BigMapsCallback(Protocol):
    def __call__(self, datasource: 'IndexDatasource', big_maps: List[BigMapData]) -> Awaitable[None]:
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


class IndexDatasource(Datasource, AsyncIOEventEmitter):
    def __init__(self, url: str, http_config: Optional[HTTPConfig] = None) -> None:
        HTTPGateway.__init__(self, url, http_config)
        AsyncIOEventEmitter.__init__(self)

    def on(self, event, f=None) -> None:
        raise RuntimeError('Do not use `on` directly')

    def emit(self, event: str, *args, **kwargs) -> None:
        if event not in ('new_listener', 'error'):
            raise RuntimeError('Do not use `emit` directly')
        super().emit(event, *args, **kwargs)

    def on_operations(self, fn: OperationsCallback) -> None:
        super().on(EventType.operations, fn)

    def on_big_maps(self, fn: BigMapsCallback) -> None:
        super().on(EventType.big_maps, fn)

    def on_rollback(self, fn: RollbackCallback) -> None:
        super().on(EventType.rollback, fn)

    def on_head(self, fn: HeadCallback) -> None:
        super().on(EventType.head, fn)

    def emit_operations(self, operations: List[OperationData], block: HeadBlockData) -> None:
        super().emit(EventType.operations, datasource=self, operations=operations, block=block)

    def emit_big_maps(self, big_maps: List[BigMapData]) -> None:
        super().emit(EventType.big_maps, datasource=self, big_maps=big_maps)

    def emit_rollback(self, from_level: int, to_level: int) -> None:
        super().emit(EventType.rollback, datasource=self, from_level=from_level, to_level=to_level)

    def emit_head(self, block: HeadBlockData) -> None:
        super().emit(EventType.head, datasource=self, block=block)
