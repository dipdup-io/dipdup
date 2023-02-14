import logging
from abc import ABC
from abc import abstractmethod
from typing import Any

from dipdup.config import DipDupConfig
from dipdup.datasources import Datasource
from dipdup.package import DipDupPackage


class CodeGenerator(ABC):
    def __init__(
        self,
        package: DipDupPackage,
        config: DipDupConfig,
        datasources: dict[str, Datasource[Any]],
    ) -> None:
        self._package = package
        self._config = config
        self._datasources = datasources
        self._logger = logging.getLogger('dipdup.codegen')

    async def init(
        self,
        force: bool = False,
        keep_schemas: bool = False,
    ) -> None:
        await self.generate_abi()
        await self.generate_schemas()
        await self.generate_types(force)
        await self.generate_hooks()
        await self.generate_handlers()

        self._package.verify()
        if keep_schemas:
            return
        self._package.cleanup()

    @abstractmethod
    async def generate_abi(self) -> None:
        ...

    @abstractmethod
    async def generate_schemas(self) -> None:
        ...

    @abstractmethod
    async def generate_types(self, force: bool) -> None:
        ...

    @abstractmethod
    async def generate_hooks(self) -> None:
        ...

    @abstractmethod
    async def generate_handlers(self) -> None:
        ...
