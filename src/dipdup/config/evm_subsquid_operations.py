from __future__ import annotations

from dataclasses import field
from typing import Any
from typing import Iterator
from typing import Literal

from pydantic.dataclasses import dataclass

from dipdup.config import AbiDatasourceConfig
from dipdup.config import ContractConfig
from dipdup.config import HandlerConfig
from dipdup.config import IndexConfig
from dipdup.config.evm_subsquid import SubsquidDatasourceConfig


@dataclass
class SubsquidOperationsHandlerConfig(HandlerConfig):
    contract: ContractConfig
    method: str
    events: tuple[Any, ...]

    def iter_arguments(self) -> Iterator[tuple[str, str]]:
        raise NotImplementedError

    def iter_imports(self, package: str) -> Iterator[tuple[str, str]]:
        raise NotImplementedError


@dataclass
class SubsquidOperationsIndexConfig(IndexConfig):
    kind: Literal['evm.subsquid.operations']
    datasource: SubsquidDatasourceConfig
    handlers: tuple[SubsquidOperationsHandlerConfig, ...] = field(default_factory=tuple)
    contracts: list[ContractConfig] = field(default_factory=list)
    abi: tuple[AbiDatasourceConfig, ...] = field(default_factory=tuple)

    first_level: int = 0
    last_level: int = 0
