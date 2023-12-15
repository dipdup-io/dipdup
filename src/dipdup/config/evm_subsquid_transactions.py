from __future__ import annotations

from dataclasses import field
from typing import TYPE_CHECKING
from typing import Literal

from pydantic.dataclasses import dataclass

from dipdup.config import AbiDatasourceConfig
from dipdup.config import HandlerConfig
from dipdup.config import IndexConfig
from dipdup.config.evm import EvmContractConfig
from dipdup.config.evm_subsquid import SubsquidDatasourceConfig
from dipdup.models.evm_node import EvmNodeTransactionsSubscription
from dipdup.subscriptions import Subscription

if TYPE_CHECKING:
    from collections.abc import Iterator


@dataclass
class SubsquidTransactionsHandlerConfig(HandlerConfig):
    """Subsquid transaction handler

    :param callback: Callback name
    :param from: Transaction sender
    :param to: Transaction receiver
    :param sighash: Method sighash
    """

    from_: EvmContractConfig | tuple[EvmContractConfig, ...] | None = None
    to: EvmContractConfig | tuple[EvmContractConfig, ...] | None = None
    sighash: str | tuple[str, ...] | None = None

    def iter_imports(self, package: str) -> Iterator[tuple[str, str]]:
        yield 'dipdup.context', 'HandlerContext'
        yield 'dipdup.models.evm_subsquid', 'SubsquidTransaction'
        yield package, 'models as models'

    def iter_arguments(self) -> Iterator[tuple[str, str]]:
        yield 'ctx', 'HandlerContext'
        yield 'transaction', 'SubsquidTransaction'


@dataclass
class SubsquidTransactionsIndexConfig(IndexConfig):
    kind: Literal['evm.subsquid.transactions']

    datasource: SubsquidDatasourceConfig
    handlers: tuple[SubsquidTransactionsHandlerConfig, ...] = field(default_factory=tuple)
    abi: AbiDatasourceConfig | tuple[AbiDatasourceConfig, ...] | None = None
    node_only: bool = False

    first_level: int = 0
    last_level: int = 0

    def get_subscriptions(self) -> set[Subscription]:
        return {EvmNodeTransactionsSubscription()}
