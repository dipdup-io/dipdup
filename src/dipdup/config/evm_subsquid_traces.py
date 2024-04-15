from __future__ import annotations

from dataclasses import field
from typing import Literal

from pydantic import ConfigDict
from pydantic import Extra
from pydantic.dataclasses import dataclass

from dipdup.config import AbiDatasourceConfig
from dipdup.config import HandlerConfig
from dipdup.config.evm_node import EvmNodeDatasourceConfig
from dipdup.config.evm_subsquid import SubsquidDatasourceConfig
from dipdup.config.evm_subsquid import SubsquidIndexConfig


@dataclass(config=ConfigDict(extra=Extra.forbid), kw_only=True)
class SubsquidTracesHandlerConfig(HandlerConfig): ...


@dataclass(config=ConfigDict(extra=Extra.forbid), kw_only=True)
class SubsquidTracesIndexConfig(SubsquidIndexConfig):
    kind: Literal['evm.subsquid.traces']

    datasource: SubsquidDatasourceConfig | EvmNodeDatasourceConfig
    handlers: tuple[SubsquidTracesHandlerConfig, ...] = field(default_factory=tuple)
    abi: AbiDatasourceConfig | tuple[AbiDatasourceConfig, ...] | None = None
    node_only: bool = False

    first_level: int = 0
    last_level: int = 0
