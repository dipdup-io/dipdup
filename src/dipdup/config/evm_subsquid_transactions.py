from __future__ import annotations

from dataclasses import field
from typing import TYPE_CHECKING
from typing import Literal

from pydantic.dataclasses import dataclass

from dipdup.config import AbiDatasourceConfig
from dipdup.config import CodegenMixin
from dipdup.config import HandlerConfig
from dipdup.config.evm import EvmContractConfig
from dipdup.config.evm_subsquid import SubsquidDatasourceConfig
from dipdup.config.evm_subsquid import SubsquidIndexConfig
from dipdup.models.evm_node import EvmNodeHeadSubscription
from dipdup.subscriptions import Subscription
from dipdup.utils import pascal_to_snake
from dipdup.utils import snake_to_pascal

if TYPE_CHECKING:
    from collections.abc import Iterator


@dataclass
class SubsquidTransactionsHandlerConfig(HandlerConfig, CodegenMixin):
    """Subsquid transaction handler

    :param callback: Callback name
    :param from_: Transaction sender
    :param to: Transaction receiver
    :param method: Method name
    """

    from_: EvmContractConfig | None = None
    to: EvmContractConfig | None = None
    method: str | None = None

    def iter_imports(self, package: str) -> Iterator[tuple[str, str]]:
        yield 'dipdup.context', 'HandlerContext'
        yield package, 'models as models'

        if self.typed_contract and self.method:
            yield 'dipdup.models.evm_subsquid', 'SubsquidTransaction'
            transaction_module = pascal_to_snake(self.method)
            transaction_cls = snake_to_pascal(self.method)
            module_name = self.typed_contract.module_name
            yield f'{package}.types.{module_name}.evm_methods.{transaction_module}', transaction_cls
        else:
            yield 'dipdup.models.evm_subsquid', 'SubsquidTransactionData'
            yield 'dipdup.models.evm_node', 'EvmNodeTransactionData'

    def iter_arguments(self) -> Iterator[tuple[str, str]]:
        yield 'ctx', 'HandlerContext'

        if self.typed_contract and self.method:
            transaction_cls = snake_to_pascal(self.method)
            yield 'transaction', f'SubsquidTransaction[{transaction_cls}]'
        else:
            yield 'transaction', 'SubsquidTransactionData | EvmNodeTransactionData'

    @property
    def typed_contract(self) -> EvmContractConfig | None:
        if self.method and self.to:
            return self.to
        return None


@dataclass
class SubsquidTransactionsIndexConfig(SubsquidIndexConfig):
    """Index that uses Subsquid Network as a datasource for transactions

    :param kind: always 'evm.subsquid.transactions'
    :param datasource: Subsquid datasource config
    :param handlers: Transaction handlers
    :param abi: One or many ABI datasource(s)
    :param node_only: Don't use Subsquid Network, only node RPC
    :param first_level: Level to start indexing from
    :param last_level: Level to stop indexing at
    """

    kind: Literal['evm.subsquid.transactions']

    datasource: SubsquidDatasourceConfig
    handlers: tuple[SubsquidTransactionsHandlerConfig, ...] = field(default_factory=tuple)
    abi: AbiDatasourceConfig | tuple[AbiDatasourceConfig, ...] | None = None
    node_only: bool = False

    first_level: int = 0
    last_level: int = 0

    def get_subscriptions(self) -> set[Subscription]:
        return {EvmNodeHeadSubscription(transactions=True)}
