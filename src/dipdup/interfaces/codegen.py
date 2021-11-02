from __future__ import annotations

from logging import Logger
from os.path import join
from typing import Set

from humps import decamelize, pascalize  # type: ignore

from dipdup.config import ContractConfig, DipDupConfig
from dipdup.const import CodegenPath
from dipdup.interfaces.const import InterfaceCodegenConst
from dipdup.interfaces.dto import ClassDefinitionDTO, EntrypointDTO, ImportDTO, InterfaceDTO, MethodDefinitionDTO, ParameterDTO, TemplateDTO
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
        logger: Logger,
    ) -> None:
        self._config: DipDupConfig = config
        self._logger: Logger = logger

    async def generate(self) -> None:
        self._logger.info('Creating `interfaces` package')
        interfaces_path = join(self._config.package_path, CodegenPath.INTERFACES_DIR)
        mkdir_p(interfaces_path)
        init_path = join(interfaces_path, CodegenPath.INIT_FILE)
        touch(init_path)

        assert isinstance(self._config.interfaces, dict)
        for interface_name, interface_config in self._config.interfaces.items():
            assert isinstance(interface_config.contract, ContractConfig)
            assert isinstance(interface_config.contract.typename, str)
            types_module_path = InterfaceCodegenConst.DOT_DELIMITER.join(
                [
                    self._config.package,
                    CodegenPath.TYPES_DIR,
                    interface_config.contract.typename,
                    CodegenPath.PARAMETER_DIR,
                ]
            )
            assert isinstance(interface_config.entrypoints, set)
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
        entrypoints: Set[str],
        logger: Logger,
    ) -> None:
        self._name: str = interface_name
        self._path: str = path
        self._types_module_path: str = types_module_path
        self._entrypoints: Set[str] = entrypoints
        self._logger: Logger = logger

    async def generate(self) -> None:
        self._logger.info(f'Generating Interface `{self._name}`')
        write(self.file_path, self.render())

    def render(self) -> str:
        from dipdup.codegen import load_template

        template = load_template(CodegenPath.INTERFACE_TEMPLATE_FILE)

        data = TemplateDTO(
            interface=InterfaceDTO(
                definition=ClassDefinitionDTO(
                    name=self._name,
                    parents=[InterfaceCodegenConst.MIXIN_NAME],
                )
            ),
            imports=[
                ImportDTO(
                    module=InterfaceCodegenConst.MIXIN_MODULE,
                    class_name=InterfaceCodegenConst.MIXIN_NAME,
                )
            ],
        )

        for entrypoint_name in self._entrypoints:
            entrypoint = EntrypointDTO(
                definition=MethodDefinitionDTO(
                    name=entrypoint_name,
                    parameters=[
                        ParameterDTO(name=InterfaceCodegenConst.PARAMETER_SELF),
                        ParameterDTO(
                            name=InterfaceCodegenConst.DEFAULT_PARAMETER_NAME,
                            type=self.parameter_type(entrypoint_name),
                        ),
                    ],
                ),
                code=[InterfaceCodegenConst.ELLIPSIS],
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
    def file_name(self) -> str:
        return f'{decamelize(self._name)}{InterfaceCodegenConst.INTERFACE_FILENAME_POSTFIX}'

    @property
    def file_path(self) -> str:
        return join(self._path, self.file_name)

    @staticmethod
    def parameter_name(name: str) -> str:
        return f'{decamelize(name)}'

    @staticmethod
    def parameter_type(name: str) -> str:
        return f'{pascalize(name)}{InterfaceCodegenConst.PARAMETER_TYPE_POSTFIX}'
