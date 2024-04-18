from __future__ import annotations

from abc import ABC
from dataclasses import field
from typing import TYPE_CHECKING
from typing import Literal

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from dipdup.config import AbiDatasourceConfig
from dipdup.config import HandlerConfig
from dipdup.config.evm import EvmIndexConfig
from dipdup.config.evm_node import EvmNodeDatasourceConfig
from dipdup.config.evm_subsquid import EvmSubsquidDatasourceConfig

if TYPE_CHECKING:
    from collections.abc import Iterator


@dataclass(config=ConfigDict(extra='forbid'), kw_only=True)
class EvmTracesHandlerConfig(HandlerConfig, ABC):
    def iter_arguments(self) -> Iterator[tuple[str, str]]:
        raise NotImplementedError

    def iter_imports(self, package: str) -> Iterator[tuple[str, str]]:
        raise NotImplementedError


@dataclass(config=ConfigDict(extra='forbid'), kw_only=True)
class EvmTracesIndexConfig(EvmIndexConfig):
    kind: Literal['evm.traces']

    datasource: EvmSubsquidDatasourceConfig | EvmNodeDatasourceConfig
    handlers: tuple[EvmTracesHandlerConfig, ...] = field(default_factory=tuple)
    abi: AbiDatasourceConfig | tuple[AbiDatasourceConfig, ...] | None = None

    first_level: int = 0
    last_level: int = 0
