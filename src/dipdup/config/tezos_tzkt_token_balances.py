from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Literal

from pydantic.dataclasses import dataclass
from pydantic.fields import Field

from dipdup.config import ContractConfig
from dipdup.config import HandlerConfig
from dipdup.config.tezos import TezosContractConfig
from dipdup.config.tezos_tzkt import TzktDatasourceConfig
from dipdup.config.tezos_tzkt import TzktIndexConfig
from dipdup.models.tezos_tzkt import TokenBalanceSubscription

if TYPE_CHECKING:
    from collections.abc import Iterator

    from dipdup.subscriptions import Subscription


@dataclass
class TzktTokenBalancesHandlerConfig(HandlerConfig):
    """Token balance handler config

    :param callback: Callback name
    :param contract: Filter by contract
    :param token_id: Filter by token ID
    """

    contract: TezosContractConfig | None = None
    token_id: int | None = None

    def iter_imports(self, package: str) -> Iterator[tuple[str, str]]:
        """This iterator result will be used in codegen to generate handler(s) template"""
        yield 'dipdup.context', 'HandlerContext'
        yield 'dipdup.models.tezos_tzkt', 'TzktTokenBalanceData'
        yield package, 'models as models'

    def iter_arguments(self) -> Iterator[tuple[str, str]]:
        """This iterator result will be used in codegen to generate handler(s) template"""
        yield 'ctx', 'HandlerContext'
        yield 'token_balance', 'TzktTokenBalanceData'


@dataclass
class TzktTokenBalancesIndexConfig(TzktIndexConfig):
    """Token balance index config

    :param kind: always `tezos.tzkt.token_balances`
    :param datasource: Index datasource to use
    :param handlers: Mapping of token transfer handlers

    :param first_level: Level to start indexing from
    :param last_level: Level to stop indexing at
    """

    kind: Literal['tezos.tzkt.token_balances']
    datasource: TzktDatasourceConfig
    handlers: tuple[TzktTokenBalancesHandlerConfig, ...] = Field(default_factory=tuple)

    first_level: int = 0
    last_level: int = 0

    def get_subscriptions(self) -> set[Subscription]:
        subs = super().get_subscriptions()
        if self.datasource.merge_subscriptions:
            subs.add(TokenBalanceSubscription())
        else:
            for handler_config in self.handlers:
                contract = (
                    handler_config.contract.address if isinstance(handler_config.contract, ContractConfig) else None
                )
                subs.add(
                    TokenBalanceSubscription(
                        contract=contract,
                        token_id=handler_config.token_id,
                    )
                )
        return subs
