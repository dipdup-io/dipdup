from __future__ import annotations

from abc import ABC
from dataclasses import field
from typing import TYPE_CHECKING
from typing import Literal

from pydantic.dataclasses import dataclass

from dipdup.config import AbiDatasourceConfig
from dipdup.config import HandlerConfig
from dipdup.config.evm_subsquid import SubsquidDatasourceConfig
from dipdup.config.evm_subsquid import SubsquidIndexConfig

if TYPE_CHECKING:
    from collections.abc import Iterator


@dataclass
class SubsquidTracesHandlerConfig(HandlerConfig, ABC):
    def iter_arguments(self) -> Iterator[tuple[str, str]]:
        raise NotImplementedError

    def iter_imports(self, package: str) -> Iterator[tuple[str, str]]:
        raise NotImplementedError


@dataclass
class SubsquidTracesIndexConfig(SubsquidIndexConfig):
    kind: Literal['evm.subsquid.traces']

    datasource: SubsquidDatasourceConfig
    handlers: tuple[SubsquidTracesHandlerConfig, ...] = field(default_factory=tuple)
    abi: AbiDatasourceConfig | tuple[AbiDatasourceConfig, ...] | None = None
    node_only: bool = False

    first_level: int = 0
    last_level: int = 0
