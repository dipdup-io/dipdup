from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Literal

from pydantic.dataclasses import dataclass

from dipdup.config import HandlerConfig
from dipdup.config.tezos_tzkt import TzktDatasourceConfig
from dipdup.config.tezos_tzkt import TzktIndexConfig

if TYPE_CHECKING:
    from collections.abc import Iterator


@dataclass
class HeadHandlerConfig(HandlerConfig):
    """Head block handler config

    :param callback: Callback name
    """

    def iter_imports(self, package: str) -> Iterator[tuple[str, str]]:
        yield 'dipdup.context', 'HandlerContext'
        yield 'dipdup.models.tezos_tzkt', 'TzktHeadBlockData'
        yield package, 'models as models'

    def iter_arguments(self) -> Iterator[tuple[str, str]]:
        yield 'ctx', 'HandlerContext'
        yield 'head', 'TzktHeadBlockData'


@dataclass
class TzktHeadIndexConfig(TzktIndexConfig):
    """Head block index config

    :param kind: always `tezos.tzkt.head`
    :param datasource: Index datasource to receive head blocks
    :param handlers: Mapping of head block handlers
    """

    kind: Literal['tezos.tzkt.head']
    datasource: TzktDatasourceConfig
    callback: str

    @property
    def first_level(self) -> int:
        return 0

    @property
    def last_level(self) -> int:
        return 0

    def __post_init_post_parse__(self) -> None:
        super().__post_init_post_parse__()
        self.handler_config = HeadHandlerConfig(callback=self.callback)
