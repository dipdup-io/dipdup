from enum import Enum
from typing import Awaitable, List, Optional, Protocol

from pyee import AsyncIOEventEmitter  # type: ignore

from dipdup.config import HTTPConfig
from dipdup.http import HTTPGateway
from dipdup.models import BigMapData, OperationData


class EventType(Enum):
    operations = 'operatitions'
    big_maps = 'big_maps'
    rollback = 'rollback'


class OperationsCallback(Protocol):
    def __call__(self, datasource: 'IndexDatasource', operations: List[OperationData]) -> Awaitable[None]:
        ...


class BigMapsCallback(Protocol):
    def __call__(self, datasource: 'IndexDatasource', big_maps: List[BigMapData]) -> Awaitable[None]:
        ...


class RollbackCallback(Protocol):
    def __call__(self, datasource: 'IndexDatasource', from_level: int, to_level: int) -> Awaitable[None]:
        ...


class IndexDatasource(HTTPGateway, AsyncIOEventEmitter):
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

    def emit_operations(self, operations: List[OperationData]) -> None:
        super().emit(EventType.operations, datasource=self, operations=operations)

    def emit_big_maps(self, big_maps: List[BigMapData]) -> None:
        super().emit(EventType.big_maps, datasource=self, big_maps=big_maps)

    def emit_rollback(self, from_level: int, to_level: int) -> None:
        super().emit(EventType.rollback, datasource=self, from_level=from_level, to_level=to_level)
