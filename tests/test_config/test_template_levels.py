from pathlib import Path

import pytest

from dipdup.config import DipDupConfig
from dipdup.config.tezos_operations import TezosOperationsIndexConfig

TEST_CONFIGS = Path(__file__).parent.parent / 'configs'

TEMPLATE = """
templates:
  hen:
    kind: tezos.operations
    datasources:
      - tzkt_mainnet
    contracts:
      - <minter>
    first_level: {first_level}
    last_level: {last_level}
    handlers:
      - callback: on_swap
        pattern:
          - type: transaction
            destination: <minter>
            entrypoint: swap
"""

INDEX = """
indexes:
  hen_from_template:
    template: hen
    first_level: {first_level}
    last_level: {last_level}
    values:
      minter: HEN_minter
"""

# NOTE: (level in the template body, level where the template is instantiated, expected level of the index)
LEVELS = (
    pytest.param(500, 1001, 1001, id='both_set'),
    pytest.param(1001, 500, 500, id='both_set_lower'),
    pytest.param(500, 0, 500, id='template_only'),
    pytest.param(0, 1001, 1001, id='instance_only'),
    pytest.param(0, 0, 0, id='neither'),
)


def load_config(tmp_path: Path, template_level: int, index_level: int | None) -> DipDupConfig:
    overlay = tmp_path / 'overlay.yaml'
    text = TEMPLATE.format(first_level=template_level, last_level=template_level)
    if index_level is not None:
        text += INDEX.format(first_level=index_level, last_level=index_level)
    overlay.write_text(text)
    return DipDupConfig.load([TEST_CONFIGS / 'dipdup.yaml', overlay])


@pytest.mark.parametrize(('template_level', 'index_level', 'expected'), LEVELS)
async def test_template_levels_yaml(tmp_path: Path, template_level: int, index_level: int, expected: int) -> None:
    config = load_config(tmp_path, template_level, index_level)
    config.initialize()

    index_config = config.indexes['hen_from_template']
    assert isinstance(index_config, TezosOperationsIndexConfig)
    assert (index_config.first_level, index_config.last_level) == (expected, expected)


@pytest.mark.parametrize(('template_level', 'index_level', 'expected'), LEVELS)
async def test_template_levels_add_index(tmp_path: Path, template_level: int, index_level: int, expected: int) -> None:
    config = load_config(tmp_path, template_level, None)
    config.initialize()

    config.add_index(
        name='hen_from_template',
        template='hen',
        values={'minter': 'HEN_minter'},
        first_level=index_level,
        last_level=index_level,
    )

    index_config = config.indexes['hen_from_template']
    assert isinstance(index_config, TezosOperationsIndexConfig)
    assert (index_config.first_level, index_config.last_level) == (expected, expected)
