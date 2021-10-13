from logging import Logger

from dipdup.config import DipDupConfig
from dipdup.interfaces.codegen import AbstractInterfacesPackageGenerator, InterfacesPackageGenerator, NullInterfacesPackageGenerator
from dipdup.types import SchemasT


class InterfacesModuleGeneratorFactory:
    def __new__(
        cls,
        config: DipDupConfig,
        schemas: SchemasT,
        logger: Logger,
    ) -> AbstractInterfacesPackageGenerator:
        if not config.interfaces:
            return NullInterfacesPackageGenerator(logger)

        return InterfacesPackageGenerator(
            config=config,
            schemas=schemas,
            logger=logger,
        )
