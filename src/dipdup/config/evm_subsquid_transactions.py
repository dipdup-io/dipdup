from __future__ import annotations

from typing import Literal

from pydantic.dataclasses import dataclass

from dipdup.config import IndexConfig
from dipdup.config.evm_subsquid import SubsquidDatasourceConfig


@dataclass
class SubsquidTransactionsIndexConfig(IndexConfig):
    kind: Literal['evm.subsquid.transactions']
    datasource: SubsquidDatasourceConfig

    ...
