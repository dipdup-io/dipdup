import os
from os.path import dirname
from os.path import join

import pytest
from _pytest.tmpdir import TempPathFactory

from dipdup.config import DipDupConfig
from dipdup.exceptions import ConfigurationError


class TestCustomConfig:
    @pytest.fixture(scope="session")
    def dummy_config_path(self) -> str:
        return join(dirname(dirname(__file__)), 'dipdup.yml')

    @staticmethod
    def appended_config_path(dummy_config_path: str, tmp_path_factory: TempPathFactory, append_raw: str) -> str:
        config_file = tmp_path_factory.mktemp('config') / 'dipdup.yml'
        with open(dummy_config_path, 'r') as f:
            config_raw = f.read()

        with open(config_file, 'a') as f:
            f.write(config_raw)
            f.write(append_raw)

        return str(config_file)

    @pytest.fixture(
        scope="session",
        params=(
            [
                """
custom:
    foo: bar
    spam:
      - eggs
      - rice

"""
            ]
        ),
    )
    def config_with_custom_section_path(self, dummy_config_path: str, tmp_path_factory: TempPathFactory, request) -> str:
        return self.appended_config_path(dummy_config_path, tmp_path_factory, request.param)

    @staticmethod
    def test_empty_custom_section(dummy_config_path: str) -> None:
        config = DipDupConfig.load([dummy_config_path], False)
        config.initialize(True)
        assert hasattr(config, 'custom')
        assert config.custom == {}

    @staticmethod
    def test_custom_section_items(config_with_custom_section_path: str) -> None:
        config = DipDupConfig.load([config_with_custom_section_path], False)
        config.initialize(True)

        assert hasattr(config, 'custom')
        assert isinstance(config.custom, dict)

        assert config.custom['foo'] == 'bar'

        spam = config.custom['spam']
        assert isinstance(spam, list)
        assert 'eggs' in spam
        assert 'rice' in spam

    @pytest.mark.parametrize(
        'value, expected',
        (
            ('${USER:-dipdup}', os.environ.get('USER')),
            ('${USER:-}', os.environ.get('USER')),
            ('${USER}', os.environ.get('USER')),
            ('${DEFINITELY_NOT_DEFINED:-default_value}', 'default_value'),
            ('${DEFINITELY_NOT_DEFINED:- some_spaces_is_ok  }', 'some_spaces_is_ok'),
        ),
    )
    def test_env_parsing_positive(self, value, expected, dummy_config_path, tmp_path_factory) -> None:
        append_raw = f"""
custom:
    var_from_env: {value}
"""
        config_path = self.appended_config_path(dummy_config_path, tmp_path_factory, append_raw)
        config = DipDupConfig.load([config_path], True)
        config.initialize(True)

        assert hasattr(config, 'custom')
        assert isinstance(config.custom, dict)

        assert config.custom['var_from_env'] == expected

    @pytest.mark.parametrize(
        'value',
        (
            '${DEFINITELY_NOT_DEFINED}',
            '${DEFINITELY_NOT_DEFINED:-}',
        ),
    )
    def test_env_parsing_negative(self, value, dummy_config_path, tmp_path_factory) -> None:
        append_raw = f"""
custom:
    var_from_env: {value}
"""
        config_path = self.appended_config_path(dummy_config_path, tmp_path_factory, append_raw)
        with pytest.raises(ConfigurationError) as exception_info:
            DipDupConfig.load([config_path], True)

        assert str(exception_info.value) == 'Environment variable `DEFINITELY_NOT_DEFINED` is not set'
