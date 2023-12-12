from __future__ import annotations

from dataclasses import field
from typing import Literal

from pydantic.dataclasses import dataclass

from dipdup.config import AbiDatasourceConfig
from dipdup.config import HandlerConfig
from dipdup.config import IndexConfig
from dipdup.config.evm_subsquid import SubsquidDatasourceConfig


@dataclass
class SubsquidTransactionsHandlerConfig(HandlerConfig): ...


@dataclass
class SubsquidTransactionsIndexConfig(IndexConfig):
    kind: Literal['evm.subsquid.transactions']

    datasource: SubsquidDatasourceConfig
    handlers: tuple[SubsquidTransactionsHandlerConfig, ...] = field(default_factory=tuple)
    abi: AbiDatasourceConfig | tuple[AbiDatasourceConfig, ...] | None = None
    node_only: bool = False

    first_level: int = 0
    last_level: int = 0
