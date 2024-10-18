from __future__ import annotations

from abc import ABC
from typing import Literal
from typing import TypeAlias

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from dipdup.config import Alias
from dipdup.config import IndexConfig
from dipdup.config import RuntimeConfig
from dipdup.config.substrate_subscan import SubstrateSubscanDatasourceConfig
from dipdup.config.substrate_subsquid import SubstrateSubsquidDatasourceConfig

SubstrateDatasourceConfigU: TypeAlias = SubstrateSubsquidDatasourceConfig | SubstrateSubscanDatasourceConfig


@dataclass(config=ConfigDict(extra='forbid'), kw_only=True)
class SubstrateRuntimeConfig(RuntimeConfig):
    """Substrate runtime config

    :param kind: Always 'substrate'
    """

    kind: Literal['substrate'] = 'substrate'


@dataclass(config=ConfigDict(extra='forbid'), kw_only=True)
class SubstrateIndexConfig(IndexConfig, ABC):
    """EVM index that use Subsquid Network as a datasource

    :param kind: starts with 'substrate'
    :param datasources: `substrate` datasources to use
    :param runtime: Substrate runtime
    """

    datasources: tuple[Alias[SubstrateDatasourceConfigU], ...]
    runtime: Alias[SubstrateRuntimeConfig]
