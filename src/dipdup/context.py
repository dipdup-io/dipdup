from typing import Any, Dict, List, Optional

from dipdup.config import ContractConfig, DipDupConfig, StaticTemplateConfig
from dipdup.datasources import DatasourceT
from dipdup.exceptions import ConfigurationError
from dipdup.models import OperationData
from dipdup.utils import FormattedLogger, reindex, restart


# TODO: Dataclasses are cool, everyone loves them. Resolve issue with pydantic in HandlerContext.
class HandlerContext:
    """Common handler context."""

    def __init__(
        self,
        datasources: Dict[str, DatasourceT],
        config: DipDupConfig,
        logger: FormattedLogger,
        template_values: Optional[Dict[str, str]],
    ) -> None:
        self.datasources = datasources
        self.config = config
        self.logger = logger
        self.template_values = template_values
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


class RollbackHandlerContext(HandlerContext):
    def __init__(
        self,
        datasources: Dict[str, DatasourceT],
        config: DipDupConfig,
        logger: FormattedLogger,
        datasource: str,
        from_level: int,
        to_level: int,
    ) -> None:
        super().__init__(datasources, config, logger, None)
        self.datasource = datasource
        self.from_level = from_level
        self.to_level = to_level
