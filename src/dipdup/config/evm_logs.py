from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Literal

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from dipdup.config import Alias
from dipdup.config import HandlerConfig
from dipdup.config.evm import EvmContractConfig
from dipdup.config.evm import EvmDatasourceConfigU
from dipdup.config.evm import EvmIndexConfig
from dipdup.models.evm_node import EvmNodeHeadSubscription
from dipdup.models.evm_node import EvmNodeLogsSubscription
from dipdup.utils import pascal_to_snake
from dipdup.utils import snake_to_pascal

if TYPE_CHECKING:
    from collections.abc import Iterator

    from dipdup.subscriptions import Subscription


@dataclass(config=ConfigDict(extra='forbid'), kw_only=True)
class EvmLogsHandlerConfig(HandlerConfig):
    """Subsquid event handler

    :param callback: Callback name
    :param contract: EVM contract
    :param name: Event name
    """

    contract: Alias[EvmContractConfig]
    name: str

    def iter_imports(self, package: str) -> Iterator[tuple[str, str]]:
        yield 'dipdup.context', 'HandlerContext'
        yield 'dipdup.models.evm', 'EvmLog'
        yield package, 'models as models'

        event_cls = snake_to_pascal(self.name) + 'Payload'
        event_module = pascal_to_snake(self.name)
        module_name = self.contract.module_name
        yield f'{package}.types.{module_name}.evm_logs.{event_module}', event_cls

    def iter_arguments(self) -> Iterator[tuple[str, str]]:
        event_cls = snake_to_pascal(self.name) + 'Payload'
        yield 'ctx', 'HandlerContext'
        yield 'log', f'EvmLog[{event_cls}]'


@dataclass(config=ConfigDict(extra='forbid'), kw_only=True)
class EvmLogsIndexConfig(EvmIndexConfig):
    """Subsquid datasource config

    :param kind: Always 'evm.logs'
    :param datasources: `evm` datasources to use
    :param handlers: Event handlers
    :param first_level: Level to start indexing from
    :param last_level: Level to stop indexing and disable this index
    """

    kind: Literal['evm.logs']
    datasources: tuple[Alias[EvmDatasourceConfigU], ...]
    handlers: tuple[EvmLogsHandlerConfig, ...]

    first_level: int = 0
    last_level: int = 0

    def get_subscriptions(self) -> set[Subscription]:
        subs: set[Subscription] = {EvmNodeHeadSubscription()}
        for handler in self.handlers:
            if address := handler.contract.address:
                subs.add(EvmNodeLogsSubscription(address=address))
        return subs
