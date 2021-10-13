from __future__ import annotations

from logging import Logger
from os.path import join
from typing import List
from typing import TYPE_CHECKING

from humps import camelize
from humps import decamelize
from humps import pascalize
from pydantic import Field
from pydantic.dataclasses import dataclass

if TYPE_CHECKING:
    from dipdup.types import SchemasT

from dipdup.config import DipDupConfig
from dipdup.const import CodegenPath
from dipdup.utils import mkdir_p, touch, write


class AbstractInterfacesPackageGenerator:
    async def generate(self) -> None:
        raise NotImplementedError


class NullInterfacesPackageGenerator(AbstractInterfacesPackageGenerator):
    """
    Separation of handling for missing interfaces config
    in the case of more complex logic here in the future
    """

    def __init__(
        self,
        logger: Logger,
    ) -> None:
        self._logger: Logger = logger

    async def generate(self) -> None:
        self._logger.info('Skip creating `interfaces` package: corresponding config section is missing')
        return None


class InterfacesPackageGenerator(AbstractInterfacesPackageGenerator):
    def __init__(
        self,
        config: DipDupConfig,
        schemas: SchemasT,
        logger: Logger,
    ) -> None:
        self._schemas: SchemasT = schemas
        self._config: DipDupConfig = config
        self._logger: Logger = logger

    async def generate(self) -> None:
        self._logger.info('Creating `interfaces` package')
        interfaces_path = join(self._config.package_path, CodegenPath.INTERFACES)
        mkdir_p(interfaces_path)
        init_path = join(interfaces_path, CodegenPath.INIT_FILE)
        touch(init_path)

        for interface_name, interface_config in self._config.interfaces.items():
            types_module_path = '.'.join(
                [
                    self._config.package,
                    CodegenPath.TYPES,
                    interface_config.contract.typename,
                    CodegenPath.PARAMETER,
                ]
            )
            interface_generator = InterfaceGenerator(
                interface_name,
                interfaces_path,
                types_module_path,
                interface_config.entrypoints,
                self._logger,
            )
            await interface_generator.generate()


class InterfaceGenerator:
    def __init__(
        self,
        interface_name: str,
        path: str,
        types_module_path: str,
        entrypoints: set,
        logger: Logger,
    ) -> None:
        self._name: str = interface_name
        self._path: str = path
        self._types_module_path: str = types_module_path
        self._entrypoints: set = entrypoints
        self._logger: Logger = logger

    async def generate(self) -> None:
        self._logger.info(f'Generating Interface `{self._name}`')
        write(self.file_path, await self.render())

    async def render(self) -> str:
        from dipdup.codegen import load_template
        template = load_template(CodegenPath.INTERFACE_TEMPLATE)

        data = TemplateDTO(interface=InterfaceDTO(name=self.class_name))

        for entrypoint_name in self._entrypoints:
            entrypoint = EntrypointDTO(
                name=self.method_name(entrypoint_name),
                parameter=ParameterDTO(
                    name='parameter',
                    type=self.parameter_type(entrypoint_name),
                ),
                code=['...'],
                decorators=['staticmethod'],
            )
            import_item = ImportDTO(
                module=f'{self._types_module_path}.{self.parameter_name(entrypoint_name)}',
                class_name=self.parameter_type(entrypoint_name),
            )
            data.interface.methods.append(entrypoint)
            data.imports.append(import_item)

        interface_code = template.render(data=data)

        return interface_code

    @property
    def class_name(self) -> str:
        return f'{pascalize(self._name)}Interface'

    @property
    def file_name(self) -> str:
        return f'{decamelize(self._name)}_interface.py'

    @property
    def file_path(self) -> str:
        return join(self._path, self.file_name)

    @staticmethod
    def method_name(name: str) -> str:
        return f'{camelize(name)}'

    @staticmethod
    def parameter_name(name: str) -> str:
        return f'{decamelize(name)}'

    @staticmethod
    def parameter_type(name: str) -> str:
        return f'{pascalize(name)}Parameter'


@dataclass
class ParameterDTO:
    name: str
    type: str = ''

    def __str__(self) -> str:
        if type:
            return f'{self.name}: {self.type}'

        return f'{self.name}'


@dataclass
class EntrypointDTO:
    name: str
    parameter: ParameterDTO
    code: List[str] = Field(default_factory=list)
    decorators: List[str] = Field(default_factory=list)
    return_type: str = 'None'


@dataclass
class ImportDTO:
    module: str
    class_name: str


@dataclass
class InterfaceDTO:
    name: str
    methods: List[EntrypointDTO] = Field(default_factory=list)


@dataclass
class TemplateDTO:
    interface: InterfaceDTO
    imports: List[ImportDTO] = Field(default_factory=list)
