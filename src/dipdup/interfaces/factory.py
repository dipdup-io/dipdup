from logging import Logger

from dipdup.config import DipDupConfig
from dipdup.interfaces.codegen import AbstractInterfacesPackageGenerator, InterfacesPackageGenerator, NullInterfacesPackageGenerator
from dipdup.types import SchemasT


class InterfacesModuleGeneratorFactory:
    def __init__(
        self,
        config: DipDupConfig,
        schemas: SchemasT,
        logger: Logger,
    ) -> None:
        self._config: DipDupConfig = config
        self._schemas: SchemasT = schemas
        self._logger: Logger = logger

    def build(self) -> AbstractInterfacesPackageGenerator:
        if not self._config.interfaces:
            return NullInterfacesPackageGenerator(self._logger)

        return InterfacesPackageGenerator(
            config=self._config,
            schemas=self._schemas,
            logger=self._logger,
        )
