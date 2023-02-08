from __future__ import annotations

from dataclasses import field
from typing import Any
from typing import Literal

from pydantic.dataclasses import dataclass

from dipdup.config import IndexConfig
from dipdup.config.evm_subsquid import EvmSubsquidDatasourceConfig


@dataclass
class EvmSubsquidEventsIndexConfig(IndexConfig):

    kind: Literal['evm.subsquid.events']
    datasource: EvmSubsquidDatasourceConfig
    handlers: tuple[Any, ...] = field(default_factory=tuple)

    first_level: int = 0
    last_level: int = 0

    def import_objects(self, package: str) -> None:
        ...
