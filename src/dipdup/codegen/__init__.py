import logging
from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import Awaitable
from typing import Callable

from pydantic import BaseModel

from dipdup.config import DipDupConfig
from dipdup.datasources import Datasource
from dipdup.package import DipDupPackage

CallbackT = Callable[..., Awaitable[None]]
TypeT = type[BaseModel]


class CodeGenerator(ABC):
    def __init__(
        self,
        config: DipDupConfig,
        package: DipDupPackage,
        datasources: dict[str, Datasource[Any]],
    ) -> None:
        self._config = config
        self._package = package
        self._datasources = datasources
        self._logger = logging.getLogger('dipdup.codegen')

    async def init(
        self,
        force: bool = False,
        keep_schemas: bool = False,
    ) -> None:
        self._package.pre_init()
        self._package.create()

        await self.generate_abi()
        await self.generate_schemas()
        await self.generate_types(force)

        await self.generate_hooks()
        await self.generate_event_hooks()
        await self.generate_handlers()

        self._package.post_init()

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
    async def generate_event_hooks(self) -> None:
        ...

    @abstractmethod
    async def generate_handlers(self) -> None:
        ...
