from typing import TYPE_CHECKING, Set, Union

from pydantic import Field
from pydantic.dataclasses import dataclass

if TYPE_CHECKING:  # pragma: no cover
    from dipdup.config import DatasourceConfigT, DipDupConfig


@dataclass
class Wallet:
    pass


@dataclass
class ExecutorConfig:
    """
    Executor config
    """

    wallet: Union[str, Wallet]
    datasource: Union[str, DatasourceConfigT] = Field(default_factory=dict)
    rpc: Set[str] = Field(default_factory=set)

    def resolve_links(self, config: DipDupConfig):
        """Encapsulating the resolve logic for proper decoupling"""

        if isinstance(self.datasource, str):
            self.datasource: DatasourceConfigT = config.get_datasource(self.datasource)  # noqa
