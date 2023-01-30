from __future__ import annotations

from typing import Iterator
from typing import Literal

from pydantic.dataclasses import dataclass
from pydantic.fields import Field

from dipdup.config import ContractConfig
from dipdup.config import HandlerConfig
from dipdup.config import IndexConfig
from dipdup.config.tzkt import TzktDatasourceConfig


@dataclass
class TokenTransferHandlerConfig(HandlerConfig, kind='handler'):
    """Token transfer handler config

    :param callback: Callback name
    :param contract: Filter by contract
    :param token_id: Filter by token ID
    :param from_: Filter by sender
    :param to: Filter by recipient
    """

    contract: ContractConfig | None = None
    token_id: int | None = None
    from_: ContractConfig | None = Field(default=None, alias='from')
    to: ContractConfig | None = None

    def iter_imports(self, package: str) -> Iterator[tuple[str, str]]:
        yield 'dipdup.context', 'HandlerContext'
        yield 'dipdup.models', 'TokenTransferData'
        yield package, 'models as models'

    def iter_arguments(self) -> Iterator[tuple[str, str]]:
        yield 'ctx', 'HandlerContext'
        yield 'token_transfer', 'TokenTransferData'


@dataclass
class TokenTransferIndexConfig(IndexConfig):
    """Token transfer index config

    :param kind: always `token_transfer`
    :param datasource: Index datasource to use
    :param handlers: Mapping of token transfer handlers

    :param first_level: Level to start indexing from
    :param last_level: Level to stop indexing at
    """

    kind: Literal['token_transfer']
    datasource: TzktDatasourceConfig
    handlers: tuple[TokenTransferHandlerConfig, ...] = Field(default_factory=tuple)

    first_level: int = 0
    last_level: int = 0

    def import_objects(self, package: str) -> None:
        for handler_config in self.handlers:
            handler_config.initialize_callback_fn(package)
