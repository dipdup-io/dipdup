import os
from pathlib import Path
from typing import Any

import pytest
from _pytest.tmpdir import TempPathFactory

from dipdup.config import DipDupConfig
from dipdup.exceptions import ConfigurationError


class TestCustomConfig:
    @pytest.fixture(scope='session')
    def dummy_config_path(self) -> Path:
        return Path(__file__).parent.parent / 'configs' / 'dipdup.yml'

    @staticmethod
    def appended_config_path(dummy_config_path: str, tmp_path_factory: TempPathFactory, append_raw: str) -> str:
        config_file = tmp_path_factory.mktemp('config') / 'dipdup.yml'
        config_raw = Path(dummy_config_path).read_text()
        config_file.write_text(config_raw + append_raw)

        return str(config_file)

    @pytest.fixture(
        scope='session',
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
    def config_with_custom_section_path(
        self, dummy_config_path: str, tmp_path_factory: TempPathFactory, request: Any
    ) -> str:
        return self.appended_config_path(dummy_config_path, tmp_path_factory, request.param)

    @staticmethod
    def test_empty_custom_section(dummy_config_path: str) -> None:
        config = DipDupConfig.load([Path(dummy_config_path)], False)
        config.initialize()
        assert hasattr(config, 'custom')
        assert config.custom == {}

    @staticmethod
    def test_custom_section_items(config_with_custom_section_path: str) -> None:
        config = DipDupConfig.load([Path(config_with_custom_section_path)], False)
        config.initialize()

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
    def test_env_parsing_positive(
        self, value: str, expected: str, dummy_config_path: str, tmp_path_factory: TempPathFactory
    ) -> None:
        append_raw = f"""
custom:
    var_from_env: {value}
"""
        config_path = self.appended_config_path(dummy_config_path, tmp_path_factory, append_raw)
        config = DipDupConfig.load([Path(config_path)], True)
        config.initialize()

        assert hasattr(config, 'custom')
        assert isinstance(config.custom, dict)

        assert config.custom['var_from_env'] == expected

    @pytest.mark.parametrize(
        'value',
        ('${DEFINITELY_NOT_DEFINED}',),
    )
    def test_env_parsing_negative(self, value: str, dummy_config_path: str, tmp_path_factory: TempPathFactory) -> None:
        append_raw = f"""
custom:
    var_from_env: {value}
"""
        config_path = self.appended_config_path(dummy_config_path, tmp_path_factory, append_raw)

        try:
            DipDupConfig.load([Path(config_path)], True)
        except ConfigurationError as exc:
            assert str(exc) == f'DipDup YAML config is invalid -> {exc.args[0]}'
            assert exc.args[0] == 'Environment variable `DEFINITELY_NOT_DEFINED` is not set'
        else:
            raise AssertionError('ConfigurationError not raised')

    @pytest.mark.parametrize(
        'value',
        (
            '${DEFINITELY_NOT_DEFINED}',
            '${DEFINITELY_NOT_DEFINED:-}',
        ),
    )
    def test_skip_commented_variables(
        self, value: str, dummy_config_path: str, tmp_path_factory: TempPathFactory
    ) -> None:
        append_raw = f"""
  #  some commented line corresponding to ENV_VARIABLE_REGEX with {value}
"""
        config_path = self.appended_config_path(dummy_config_path, tmp_path_factory, append_raw)
        DipDupConfig.load([Path(config_path)], True)
