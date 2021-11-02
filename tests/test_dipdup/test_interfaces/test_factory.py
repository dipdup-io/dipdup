import logging
from typing import Type

import pytest
from _pytest.fixtures import FixtureRequest

from dipdup.config import DipDupConfig
from dipdup.interfaces.codegen import AbstractInterfacesPackageGenerator, InterfacesPackageGenerator, NullInterfacesPackageGenerator
from dipdup.interfaces.factory import InterfacesModuleGeneratorFactory


class TestFactory:
    def test_fixtures(self, dipdup_config_without_interfaces: DipDupConfig, dipdup_config_with_interfaces: DipDupConfig) -> None:
        assert isinstance(dipdup_config_without_interfaces, DipDupConfig)
        assert dipdup_config_without_interfaces.interfaces == dict()

        assert isinstance(dipdup_config_with_interfaces, DipDupConfig)
        assert isinstance(dipdup_config_with_interfaces.interfaces, dict)
        assert len(dipdup_config_with_interfaces.interfaces) == 1

    @pytest.mark.parametrize(
        'dipdup_config_fixture_name, expected_generator_type',
        [
            ('dipdup_config_with_interfaces', InterfacesPackageGenerator),
            ('dipdup_config_without_interfaces', NullInterfacesPackageGenerator),
        ],
    )
    def test_module_generator_factory(
        self,
        dipdup_config_fixture_name: str,
        expected_generator_type: Type[AbstractInterfacesPackageGenerator],
        request: FixtureRequest,
    ) -> None:
        dipdup_config: DipDupConfig = request.getfixturevalue(dipdup_config_fixture_name)
        assert isinstance(dipdup_config, DipDupConfig)

        factory = InterfacesModuleGeneratorFactory(
            config=dipdup_config,
            logger=logging.getLogger(),
        )
        generator = factory.build()
        assert isinstance(generator, AbstractInterfacesPackageGenerator)
        assert isinstance(generator, expected_generator_type)
        assert callable(generator.generate)
