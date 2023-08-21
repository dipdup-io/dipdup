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
from dipdup.models.tezos_tzkt import TokenTransferSubscription

if TYPE_CHECKING:
    from collections.abc import Iterator

    from dipdup.subscriptions import Subscription


@dataclass
class TzktTokenTransfersHandlerConfig(HandlerConfig):
    """Token transfer handler config

    :param callback: Callback name
    :param contract: Filter by contract
    :param token_id: Filter by token ID
    :param from_: Filter by sender
    :param to: Filter by recipient
    """

    contract: TezosContractConfig | None = None
    token_id: int | None = None
    # FIXME: Can't use `from_` field alias in dataclass
    # FIXME: See https://github.com/pydantic/pydantic/issues/4286 (fixed in upcoming v2)
    from_: TezosContractConfig | None = None
    to: TezosContractConfig | None = None

    def iter_imports(self, package: str) -> Iterator[tuple[str, str]]:
        yield 'dipdup.context', 'HandlerContext'
        yield 'dipdup.models.tezos_tzkt', 'TzktTokenTransferData'
        yield package, 'models as models'

    def iter_arguments(self) -> Iterator[tuple[str, str]]:
        yield 'ctx', 'HandlerContext'
        yield 'token_transfer', 'TzktTokenTransferData'


@dataclass
class TzktTokenTransfersIndexConfig(TzktIndexConfig):
    """Token transfer index config

    :param kind: always `tezos.tzkt.token_transfers`
    :param datasource: Index datasource to use
    :param handlers: Mapping of token transfer handlers

    :param first_level: Level to start indexing from
    :param last_level: Level to stop indexing at
    """

    kind: Literal['tezos.tzkt.token_transfers']
    datasource: TzktDatasourceConfig
    handlers: tuple[TzktTokenTransfersHandlerConfig, ...] = Field(default_factory=tuple)

    first_level: int = 0
    last_level: int = 0

    def get_subscriptions(self) -> set[Subscription]:
        subs = super().get_subscriptions()
        if self.datasource.merge_subscriptions:
            subs.add(TokenTransferSubscription())  # type: ignore[call-arg]
        else:
            for handler_config in self.handlers:
                contract = (
                    handler_config.contract.address if isinstance(handler_config.contract, ContractConfig) else None
                )
                from_ = handler_config.from_.address if isinstance(handler_config.from_, ContractConfig) else None
                to = handler_config.to.address if isinstance(handler_config.to, ContractConfig) else None
                subs.add(
                    TokenTransferSubscription(  # type: ignore[call-arg]
                        contract=contract,
                        from_=from_,
                        to=to,
                        token_id=handler_config.token_id,
                    )
                )
        return subs
