from typing import TYPE_CHECKING, Set, Union

from pydantic import Field
from pydantic.dataclasses import dataclass

if TYPE_CHECKING:  # pragma: no cover
    from dipdup.config import DatasourceConfigT, DipDupConfig


class WalletConfigInterface:
    def get_public_key(self) -> str:
        raise NotImplementedError

    def get_private_key(self) -> str:
        raise NotImplementedError


@dataclass
class WalletConfig(WalletConfigInterface):
    """
    Naive Wallet realization
    """

    def get_public_key(self) -> str:
        return self.public_key

    def get_private_key(self) -> str:
        return self.private_key

    public_key: str
    private_key: str


@dataclass
class ExecutorConfig:
    """
    Executor config
    """

    wallet: Union[str, WalletConfig]
    datasource: Union[str, DatasourceConfigT] = Field(default_factory=dict)
    rpc: Set[str] = Field(default_factory=set)

    def resolve_links(self, config: DipDupConfig):
        """Encapsulating the resolve logic for proper decoupling"""

        if isinstance(self.datasource, str):
            self.datasource: DatasourceConfigT = config.get_datasource(self.datasource)  # noqa
