from logging import Logger

from dipdup.config import DipDupConfig
from dipdup.interfaces.codegen import AbstractInterfacesPackageGenerator, InterfacesPackageGenerator, NullInterfacesPackageGenerator


class InterfacesModuleGeneratorFactory:
    def __init__(
        self,
        config: DipDupConfig,
        logger: Logger,
    ) -> None:
        self._config: DipDupConfig = config
        self._logger: Logger = logger

    def build(self) -> AbstractInterfacesPackageGenerator:
        if not self._config.interfaces:
            return NullInterfacesPackageGenerator(self._logger)

        return InterfacesPackageGenerator(
            config=self._config,
            logger=self._logger,
        )
