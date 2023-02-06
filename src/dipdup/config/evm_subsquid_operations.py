from __future__ import annotations

from dataclasses import field
from typing import Any
from typing import Literal

from pydantic.dataclasses import dataclass

from dipdup.config import ContractConfig
from dipdup.config import IndexConfig
from dipdup.config.subsquid import SubsquidDatasourceConfig


@dataclass
class EvmSubsquidOperationsIndexConfig(IndexConfig):
    kind: Literal['evm.subsquid.operations']
    datasource: SubsquidDatasourceConfig
    handlers: tuple[Any, ...]
    contracts: list[ContractConfig] = field(default_factory=list)

    first_level: int = 0
    last_level: int = 0

    def import_objects(self, package: str) -> None:
        ...
