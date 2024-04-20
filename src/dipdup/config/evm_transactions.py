from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Literal

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from dipdup.config import Alias
from dipdup.config import CodegenMixin
from dipdup.config import HandlerConfig
from dipdup.config.evm import EvmContractConfig
from dipdup.config.evm import EvmDatasourceConfigU
from dipdup.config.evm import EvmIndexConfig
from dipdup.models.evm_node import EvmNodeHeadSubscription
from dipdup.subscriptions import Subscription
from dipdup.utils import pascal_to_snake
from dipdup.utils import snake_to_pascal

if TYPE_CHECKING:
    from collections.abc import Iterator


@dataclass(config=ConfigDict(extra='forbid'), kw_only=True)
class EvmTransactionsHandlerConfig(HandlerConfig, CodegenMixin):
    """Subsquid transaction handler

    :param callback: Callback name
    :param from_: Transaction sender
    :param to: Transaction receiver
    :param method: Method name
    """

    # FIXME: Can't use `from_` field alias in dataclasses
    from_: Alias[EvmContractConfig] | None = None
    to: Alias[EvmContractConfig] | None = None
    method: str | None = None

    def iter_imports(self, package: str) -> Iterator[tuple[str, str]]:
        yield 'dipdup.context', 'HandlerContext'
        yield package, 'models as models'

        if self.typed_contract and self.method:
            yield 'dipdup.models.evm', 'EvmTransaction'
            transaction_module = pascal_to_snake(self.method)
            transaction_cls = snake_to_pascal(self.method) + 'Input'
            module_name = self.typed_contract.module_name
            yield f'{package}.types.{module_name}.evm_transactions.{transaction_module}', transaction_cls
        else:
            yield 'dipdup.models.evm', 'EvmTransactionData'

    def iter_arguments(self) -> Iterator[tuple[str, str]]:
        yield 'ctx', 'HandlerContext'

        if self.typed_contract and self.method:
            transaction_cls = snake_to_pascal(self.method) + 'Input'
            yield 'transaction', f'EvmTransaction[{transaction_cls}]'
        else:
            yield 'transaction', 'EvmTransactionData'

    @property
    def typed_contract(self) -> EvmContractConfig | None:
        if self.method and self.to:
            return self.to
        return None


@dataclass(config=ConfigDict(extra='forbid'), kw_only=True)
class EvmTransactionsIndexConfig(EvmIndexConfig):
    """Index that uses Subsquid Network as a datasource for transactions

    :param kind: always 'evm.transactions'
    :param datasources: `evm` datasources to use
    :param handlers: Transaction handlers
    :param first_level: Level to start indexing from
    :param last_level: Level to stop indexing at
    """

    kind: Literal['evm.transactions']

    datasources: tuple[Alias[EvmDatasourceConfigU], ...]
    handlers: tuple[EvmTransactionsHandlerConfig, ...]

    first_level: int = 0
    last_level: int = 0

    def get_subscriptions(self) -> set[Subscription]:
        return {EvmNodeHeadSubscription(transactions=True)}
