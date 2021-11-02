from copy import deepcopy
from logging import Logger, getLogger

import pytest

from dipdup.config import ContractConfig, DipDupConfig, TzktDatasourceConfig
from dipdup.interfaces.config import InterfaceConfig


@pytest.fixture
def interface_config() -> InterfaceConfig:
    return InterfaceConfig(
        contract='test_contract',
        datasource='test_datasource',
        entrypoints={'spam', 'eggs'},
    )


@pytest.fixture
def contract_config() -> ContractConfig:
    return ContractConfig(
        address='tz_dummy_address_0000000000000000036',
        typename='dummy_contract_typename',
    )


@pytest.fixture
def datasource_config() -> TzktDatasourceConfig:
    return TzktDatasourceConfig(
        kind='tzkt',
        url='https://example.com/',
    )


@pytest.fixture
def dipdup_config_without_interfaces(
    contract_config: ContractConfig,
    datasource_config: TzktDatasourceConfig,
) -> DipDupConfig:
    config = DipDupConfig(
        spec_version='foo',
        package='bar',
        datasources={},
    )
    config.contracts = dict(test_contract=contract_config)
    config.datasources = dict(test_datasource=datasource_config)

    return config


@pytest.fixture
def dipdup_config_with_interfaces(dipdup_config_without_interfaces: DipDupConfig, interface_config: InterfaceConfig) -> DipDupConfig:
    config: DipDupConfig = deepcopy(dipdup_config_without_interfaces)
    assert isinstance(config.interfaces, dict)
    config.interfaces['foo_bar'] = interface_config
    return config


@pytest.fixture
def logger() -> Logger:
    return getLogger()
