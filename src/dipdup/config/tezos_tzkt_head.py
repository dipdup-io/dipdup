from __future__ import annotations

from typing import Iterator
from typing import Literal

from pydantic.dataclasses import dataclass

from dipdup.config import HandlerConfig
from dipdup.config import IndexConfig
from dipdup.config.tzkt import TzktDatasourceConfig


@dataclass
class HeadHandlerConfig(HandlerConfig, kind='handler'):
    """Head block handler config

    :param callback: Callback name
    """

    def iter_imports(self, package: str) -> Iterator[tuple[str, str]]:
        yield 'dipdup.context', 'HandlerContext'
        yield 'dipdup.models.tzkt', 'HeadBlockData'
        yield package, 'models as models'

    def iter_arguments(self) -> Iterator[tuple[str, str]]:
        yield 'ctx', 'HandlerContext'
        yield 'head', 'HeadBlockData'


@dataclass
class HeadIndexConfig(IndexConfig):
    """Head block index config

    :param kind: always `head`
    :param datasource: Index datasource to receive head blocks
    :param handlers: Mapping of head block handlers
    """

    kind: Literal['tezos.tzkt.head']
    datasource: TzktDatasourceConfig
    handlers: tuple[HeadHandlerConfig, ...]

    @property
    def first_level(self) -> int:
        return 0

    @property
    def last_level(self) -> int:
        return 0

    def import_objects(self, package: str) -> None:
        for handler_config in self.handlers:
            handler_config.initialize_callback_fn(package)
