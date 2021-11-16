from typing import Any
from typing import Callable
from typing import Dict
from typing import TYPE_CHECKING
from typing import Union

from dipdup.config import ContractConfig
from dipdup.config import TzktDatasourceConfig

if TYPE_CHECKING:  # pragma: no cover
    from dipdup.config import ContractConfig, DipDupConfig

SchemasT = Dict[TzktDatasourceConfig, Dict[str, Dict[str, Any]]]


class ConfigEntityName(str):
    @staticmethod
    def get_resolve_method(config: DipDupConfig) -> Callable:
        raise NotImplementedError


class ContractConfigName(ConfigEntityName):
    @staticmethod
    def get_resolve_method(config: DipDupConfig) -> Callable:
        return config.get_contract


class DatasourceConfigEntityName(ConfigEntityName):
    @staticmethod
    def get_resolve_method(config: DipDupConfig) -> Callable:
        return config.get_datasource


ContractConfigEntity = Union[ContractConfig, ContractConfigName]
# DatasourceConfigEntity = Union[DatasourceConfig, ContractConfigEntityName]
