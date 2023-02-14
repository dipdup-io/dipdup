import logging
from abc import ABC
from abc import abstractmethod
from shutil import rmtree
from typing import Any

from dipdup.config import DipDupConfig
from dipdup.datasources import Datasource
from dipdup.package import DipDupPackage
from dipdup.utils import import_submodules


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
        self.verify_package()

        if keep_schemas:
            return

        rmtree(self._package.schemas, ignore_errors=True)
        rmtree(self._package.abi, ignore_errors=True)

    def verify_package(self) -> None:
        import_submodules(self._config.package)

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
