from abc import abstractmethod
from typing import Awaitable, List, Protocol, Set

from dipdup.config import HTTPConfig
from dipdup.http import HTTPGateway
from dipdup.models import BigMapData, HeadBlockData, OperationData


class OperationsCallback(Protocol):
    def __call__(self, datasource: 'IndexDatasource', operations: List[OperationData]) -> Awaitable[None]:
        ...


class BigMapsCallback(Protocol):
    def __call__(self, datasource: 'IndexDatasource', big_maps: List[BigMapData]) -> Awaitable[None]:
        ...


class RollbackCallback(Protocol):
    def __call__(self, datasource: 'IndexDatasource', from_level: int, to_level: int) -> Awaitable[None]:
        ...


class HeadCallback(Protocol):
    def __call__(self, datasource: 'IndexDatasource', head: HeadBlockData) -> Awaitable[None]:
        ...


class Datasource(HTTPGateway):
    @abstractmethod
    async def run(self) -> None:
        ...


class IndexDatasource(Datasource):
    def __init__(self, url: str, http_config: HTTPConfig) -> None:
        super().__init__(url, http_config)
        self._on_head: Set[HeadCallback] = set()
        self._on_operations: Set[OperationsCallback] = set()
        self._on_big_maps: Set[BigMapsCallback] = set()
        self._on_rollback: Set[RollbackCallback] = set()

    def on_head(self, fn: HeadCallback) -> None:
        self._on_head.add(fn)

    def on_operations(self, fn: OperationsCallback) -> None:
        self._on_operations.add(fn)

    def on_big_maps(self, fn: BigMapsCallback) -> None:
        self._on_big_maps.add(fn)

    def on_rollback(self, fn: RollbackCallback) -> None:
        self._on_rollback.add(fn)

    async def emit_head(self, head: HeadBlockData) -> None:
        for fn in self._on_head:
            await fn(self, head)

    async def emit_operations(self, operations: List[OperationData]) -> None:
        for fn in self._on_operations:
            await fn(self, operations)

    async def emit_big_maps(self, big_maps: List[BigMapData]) -> None:
        for fn in self._on_big_maps:
            await fn(self, big_maps)

    async def emit_rollback(self, from_level: int, to_level: int) -> None:
        for fn in self._on_rollback:
            await fn(self, from_level, to_level)
