from __future__ import annotations

from dataclasses import field
from typing import Literal

from pydantic.dataclasses import dataclass

from dipdup.config import AbiDatasourceConfig
from dipdup.config import HandlerConfig
from dipdup.config.evm_subsquid import SubsquidDatasourceConfig
from dipdup.config.evm_subsquid import SubsquidIndexConfig


@dataclass
class SubsquidTracesHandlerConfig(HandlerConfig): ...


@dataclass
class SubsquidTracesIndexConfig(SubsquidIndexConfig):
    kind: Literal['evm.subsquid.traces']

    datasource: SubsquidDatasourceConfig
    handlers: tuple[SubsquidTracesHandlerConfig, ...] = field(default_factory=tuple)
    abi: AbiDatasourceConfig | tuple[AbiDatasourceConfig, ...] | None = None
    node_only: bool = False

    first_level: int = 0
    last_level: int = 0
