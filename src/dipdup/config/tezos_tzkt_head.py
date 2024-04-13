from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Literal

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from dipdup.config import HandlerConfig
from dipdup.config.tezos_tzkt import TezosTzktDatasourceConfig
from dipdup.config.tezos_tzkt import TezosTzktIndexConfig

if TYPE_CHECKING:
    from collections.abc import Iterator


@dataclass(config=ConfigDict(extra='forbid'), kw_only=True)
class TezosTzktHeadHandlerConfig(HandlerConfig):
    """Head block handler config

    :param callback: Callback name
    """

    def iter_imports(self, package: str) -> Iterator[tuple[str, str]]:
        yield 'dipdup.context', 'HandlerContext'
        yield 'dipdup.models.tezos_tzkt', 'TezosTzktHeadBlockData as HeadBlockData'
        yield package, 'models as models'

    def iter_arguments(self) -> Iterator[tuple[str, str]]:
        yield 'ctx', 'HandlerContext'
        yield 'head', 'HeadBlockData'


@dataclass(config=ConfigDict(extra='forbid'), kw_only=True)
class TezosTzktHeadIndexConfig(TezosTzktIndexConfig):
    """Head block index config

    :param kind: always 'tezos.tzkt.head'
    :param callback: Callback name
    :param datasource: Index datasource to receive head blocks
    :param handlers: Mapping of head block handlers
    """

    kind: Literal['tezos.tzkt.head']
    datasource: TezosTzktDatasourceConfig
    callback: str

    @property
    def first_level(self) -> int:
        return 0

    @property
    def last_level(self) -> int:
        return 0

    def __post_init__(self) -> None:
        super().__post_init__()
        self.handler_config = TezosTzktHeadHandlerConfig(callback=self.callback)
