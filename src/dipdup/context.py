from typing import Any, Dict, List, Optional

from dipdup.config import ContractConfig, DipDupConfig, StaticTemplateConfig
from dipdup.datasources import DatasourceT
from dipdup.exceptions import ConfigurationError
from dipdup.models import OperationData
from dipdup.utils import reindex, restart


class HandlerContext:
    """Common handler context."""

    def __init__(
        self,
        datasources: Dict[str, DatasourceT],
        config: DipDupConfig,
    ) -> None:
        self.datasources = datasources
        self.config = config
        self._updated: bool = False

    def commit(self) -> None:
        """Spawn indexes after handler execution"""
        self._updated = True

    def reset(self) -> None:
        self._updated = False

    @property
    def updated(self) -> bool:
        return self._updated

    async def reindex(self) -> None:
        await reindex()

    async def restart(self) -> None:
        await restart()

    def add_contract(self, name: str, address: str, typename: Optional[str] = None) -> None:
        if name in self.config.contracts:
            raise ConfigurationError(f'Contract `{name}` is already exists')
        self.config.contracts[name] = ContractConfig(
            address=address,
            typename=typename,
        )
        self._updated = True

    def add_index(self, name: str, template: str, values: Dict[str, Any]) -> None:
        if name in self.config.indexes:
            raise ConfigurationError(f'Index `{name}` is already exists')
        self.config.get_template(template)
        self.config.indexes[name] = StaticTemplateConfig(
            template=template,
            values=values,
        )
        self._updated = True


class OperationHandlerContext(HandlerContext):
    """Operation index handler context (first argument)"""

    def __init__(
        self,
        datasources: Dict[str, DatasourceT],
        config: DipDupConfig,
        operations: List[OperationData],
        template_values: Optional[Dict[str, str]],
    ) -> None:
        super().__init__(datasources, config)
        self.operations = operations
        self.template_values = template_values


class BigMapHandlerContext(HandlerContext):
    """Big map index handler context (first argument)"""

    def __init__(
        self,
        datasources: Dict[str, DatasourceT],
        config: DipDupConfig,
        template_values: Optional[Dict[str, str]],
    ) -> None:
        super().__init__(datasources, config)
        self.template_values = template_values


class RollbackHandlerContext(HandlerContext):
    def __init__(
        self,
        datasources: Dict[str, DatasourceT],
        config: DipDupConfig,
        datasource: str,
        from_level: int,
        to_level: int,
    ) -> None:
        super().__init__(datasources, config)
        self.datasource = datasource
        self.from_level = from_level
        self.to_level = to_level
