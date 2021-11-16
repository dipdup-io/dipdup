from typing import TYPE_CHECKING, Optional, Set, Union

from pydantic import Field
from pydantic.dataclasses import dataclass

from dipdup.types import ConfigEntityName

if TYPE_CHECKING:  # pragma: no cover
    from dipdup.types import ContractConfigEntity
    from dipdup.config import ContractConfig, DatasourceConfigT, DipDupConfig


@dataclass
class InterfaceConfig:
    """Interface config

    :param contract: Alias of contract being indexed in `Interfaces` section
    :param datasource: Aliases of datasource being indexed in `Interfaces` section
    :param entrypoints: Optional set of Contract entrypoints
    """

    contract: ContractConfigEntity = Field(default_factory=dict)
    datasource: Union[str, 'DatasourceConfigT'] = Field(default_factory=dict)
    entrypoints: Optional[Set[str]] = Field(default_factory=set)

    def resolve_links(self, config: 'DipDupConfig') -> None:
        """Encapsulating the resolve logic for proper decoupling"""

        if isinstance(self.contract, ConfigEntityName):
            # Todo: PoC for common solution
            resolve = self.contract.get_resolve_method(config)
            self.contract: ContractConfig = resolve(self.contract)  # noqa
        if isinstance(self.datasource, str):
            self.datasource: DatasourceConfigT = config.get_datasource(self.datasource)  # noqa
