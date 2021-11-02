import ast
import inspect
from logging import Logger

import pytest
from pytest_mock import MockerFixture

from dipdup.config import DipDupConfig
from dipdup.interfaces.codegen import (AbstractInterfacesPackageGenerator, InterfaceGenerator, InterfacesPackageGenerator,
                                       NullInterfacesPackageGenerator)
from dipdup.interfaces.config import InterfaceConfig


class TestCodegen:
    @pytest.fixture()
    def interface_generator(self, interface_config: InterfaceConfig, logger: Logger) -> InterfaceGenerator:
        assert isinstance(interface_config.entrypoints, set)
        return InterfaceGenerator(
            interface_name='foo_bar',
            path='test/path',
            types_module_path='some.test.module.path',
            entrypoints=interface_config.entrypoints,
            logger=logger,
        )

    @pytest.mark.parametrize(
        'expected_line',
        (
            'from dipdup.interfaces.mixin import InterfaceMixin',
            'from some.test.module.path.spam import SpamParameter',
            'from some.test.module.path.eggs import EggsParameter',
            'class FooBarInterface(InterfaceMixin):',
            '    async def spam(self, parameter: SpamParameter) -> None:',
            '    async def eggs(self, parameter: EggsParameter) -> None:',
        ),
    )
    @pytest.mark.asyncio
    async def test_interface_render(self, interface_generator: InterfaceGenerator, expected_line: str) -> None:
        await interface_generator._render()

        assert expected_line in interface_generator._code.splitlines()

    @pytest.mark.asyncio
    async def test_interface_generator(self, interface_generator: InterfaceGenerator, mocker: MockerFixture) -> None:
        mocked_write = mocker.patch.object(inspect.getmodule(interface_generator), 'write')
        mocked_info = mocker.patch.object(interface_generator._logger, 'info')

        assert mocked_info.call_count == 0
        assert mocked_write.call_count == 0

        await interface_generator.generate()

        assert mocked_info.call_count == 1
        assert mocked_write.call_count == 1
        assert mocked_write.call_args[0][0] == interface_generator.file_path

    @pytest.mark.asyncio
    async def test_interface_package_generator(
        self, dipdup_config_with_interfaces: DipDupConfig, logger: Logger, mocker: MockerFixture
    ) -> None:
        config = dipdup_config_with_interfaces
        assert isinstance(config.interfaces, dict)
        for interface in config.interfaces.values():
            interface.resolve_links(config)

        package_generator = InterfacesPackageGenerator(
            config=config,
            logger=logger,
        )

        mocked_info = mocker.patch.object(logger, 'info')
        mocked_mkdir_p = mocker.patch.object(inspect.getmodule(package_generator), 'mkdir_p')
        mocked_touch = mocker.patch.object(inspect.getmodule(package_generator), 'touch')
        mocked_interface_constructor = mocker.patch(
            'dipdup.interfaces.codegen.InterfaceGenerator.__init__',
            return_value=None,
        )
        mocked_interface_generate = mocker.patch('dipdup.interfaces.codegen.InterfaceGenerator.generate')

        assert mocked_info.call_count == 0
        assert mocked_mkdir_p.call_count == 0
        assert mocked_touch.call_count == 0
        assert mocked_interface_generate.call_count == 0

        config.package_path = 'foo/bar'

        await package_generator.generate()

        assert mocked_info.call_count == 1
        assert mocked_mkdir_p.call_count == 1
        assert mocked_touch.call_count == 1
        assert mocked_interface_generate.call_count == 1
        assert mocked_interface_constructor.call_count == 1
        assert isinstance(config.interfaces, dict)
        assert mocked_interface_constructor.call_args[0][0] == list(config.interfaces.keys())[0]
        assert mocked_interface_constructor.call_args[0][1] == f'{config.package_path}/interfaces'
        assert mocked_interface_constructor.call_args[0][3] == list(config.interfaces.values())[0].entrypoints

    @pytest.mark.asyncio
    async def test_null_interface_package_generator(self, logger: Logger, mocker: MockerFixture) -> None:
        mocked_info = mocker.patch.object(logger, 'info')
        package_generator = NullInterfacesPackageGenerator(logger=logger)

        assert mocked_info.call_count == 0

        await package_generator.generate()

        assert mocked_info.call_count == 1

    @pytest.mark.asyncio
    async def test_abstract_interface_package_generator(self) -> None:
        package_generator = AbstractInterfacesPackageGenerator()
        with pytest.raises(NotImplementedError):
            await package_generator.generate()
