from __future__ import annotations

from ast import AST, AsyncFunctionDef, ClassDef, Constant, Expr, ImportFrom, Load, Module, Name, alias, arg, arguments, unparse
from logging import Logger
from os.path import join
from typing import Set

from black import Mode, TargetVersion, format_str
from humps import camelize, decamelize, pascalize  # type: ignore

from dipdup.config import ContractConfig, DipDupConfig
from dipdup.const import CodegenPath
from dipdup.interfaces.const import InterfaceCodegenConst
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
        self._code: str = ''

    async def generate(self) -> None:
        self._logger.info(f'Generating Interface `{self._name}`')
        await self._render()
        await self._reformat()
        write(self.file_path, self._code)

    async def _render(self) -> None:
        interface_ast: AST = await self._build_ast()
        self._code: str = unparse(interface_ast)

    async def _build_ast(self) -> AST:
        result_tree = Module(body=[], type_ignores=[])
        import_tree_list = [
            ImportFrom(
                module=InterfaceCodegenConst.MIXIN_MODULE,
                names=[alias(name=InterfaceCodegenConst.MIXIN_NAME)],
                level=0
            ),
        ]
        class_tree = ClassDef(
            name=self.get_class_name(),
            bases=[Name(id=InterfaceCodegenConst.MIXIN_NAME, ctx=Load())],
            keywords=[],
            body=[],
            decorator_list=[],
        )

        for entrypoint_name in self._entrypoints:
            entrypoint = AsyncFunctionDef(
                lineno=None,
                name=self.get_method_name(entrypoint_name),
                args=arguments(
                    posonlyargs=[],
                    args=[
                        arg(arg=InterfaceCodegenConst.PARAMETER_SELF),
                        arg(
                            arg=InterfaceCodegenConst.DEFAULT_PARAMETER_NAME,
                            annotation=Name(id=self.get_parameter_type(entrypoint_name), ctx=Load()),
                        )
                    ],
                    kwonlyargs=[],
                    kw_defaults=[],
                    defaults=[]
                ),
                body=[
                    Expr(value=Constant(value=Ellipsis)),
                ],
                returns=Constant(value=None),
                decorator_list=[],
            )
            import_tree = ImportFrom(
                module=self.get_import_module(entrypoint_name),
                names=[alias(name=self.get_parameter_type(entrypoint_name))],
                level=0,
            )
            class_tree.body.append(entrypoint)
            import_tree_list.append(import_tree)

        result_tree.body += import_tree_list
        result_tree.body.append(class_tree)

        return result_tree

    async def _reformat(self) -> None:
        self._code: str = format_str(
            src_contents=self._code,
            mode=Mode(
                target_versions={TargetVersion.PY38},
                line_length=140,
                string_normalization=False,
            ),
        )

    @property
    def file_name(self) -> str:
        return f'{decamelize(self._name)}{InterfaceCodegenConst.INTERFACE_FILENAME_POSTFIX}'

    @property
    def file_path(self) -> str:
        return join(self._path, self.file_name)

    def get_import_module(self, name: str) -> str:
        return f'{self._types_module_path}.{self.get_parameter_name(name)}'

    def get_class_name(self) -> str:
        return f'{pascalize(self._name)}{InterfaceCodegenConst.INTERFACE_CLASS_POSTFIX}'

    @staticmethod
    def get_method_name(name) -> str:
        return f'{camelize(name)}'

    @staticmethod
    def get_parameter_name(name: str) -> str:
        return f'{decamelize(name)}'

    @staticmethod
    def get_parameter_type(name: str) -> str:
        return f'{pascalize(name)}{InterfaceCodegenConst.PARAMETER_TYPE_POSTFIX}'
