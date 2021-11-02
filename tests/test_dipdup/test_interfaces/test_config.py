import pytest

from dipdup.config import ContractConfig, DipDupConfig, TzktDatasourceConfig
from dipdup.interfaces.config import InterfaceConfig


class TestConfig:
    @pytest.mark.parametrize(
        'property_name, initial_type, expected_type',
        [
            ('contract', str, ContractConfig),
            ('datasource', str, TzktDatasourceConfig),
        ],
    )
    def test_resolve_interface_properties(
        self,
        property_name: str,
        initial_type: type,
        expected_type: type,
        dipdup_config_with_interfaces: DipDupConfig,
    ) -> None:
        assert isinstance(dipdup_config_with_interfaces, DipDupConfig)

        assert isinstance(dipdup_config_with_interfaces.interfaces, dict)
        for interface in dipdup_config_with_interfaces.interfaces.values():
            assert isinstance(interface, InterfaceConfig)

            assert isinstance(interface.__getattribute__(property_name), initial_type)
            interface.resolve_links(dipdup_config_with_interfaces)
            assert isinstance(interface.__getattribute__(property_name), expected_type)
