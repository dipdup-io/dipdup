from pathlib import Path

import pytest

from dipdup.config import DipDupConfig
from dipdup.config import IndexConfig
from dipdup.config.tezos_head import TezosHeadIndexConfig
from dipdup.config.tezos_operations import TezosOperationsUnfilteredIndexConfig

TEST_CONFIGS = Path(__file__).parent.parent / 'configs'

# NOTE: Index kinds whose `handlers` are derived from `callback` instead of being declared
TEMPLATES = (
    pytest.param(
        """
templates:
  tpl:
    kind: tezos.head
    datasources:
      - <datasource>
    callback: on_<name>
""",
        TezosHeadIndexConfig,
        id='tezos.head',
    ),
    pytest.param(
        """
templates:
  tpl:
    kind: tezos.operations_unfiltered
    datasources:
      - <datasource>
    types:
      - transaction
    callback: on_<name>
""",
        TezosOperationsUnfilteredIndexConfig,
        id='tezos.operations_unfiltered',
    ),
)

INDEX = """
indexes:
  from_template:
    template: tpl
    values:
      datasource: tzkt_mainnet
      name: head
"""

VALUES = {'datasource': 'tzkt_mainnet', 'name': 'head'}


def load_config(tmp_path: Path, text: str) -> DipDupConfig:
    overlay = tmp_path / 'overlay.yaml'
    overlay.write_text(text)
    return DipDupConfig.load([TEST_CONFIGS / 'dipdup.yaml', overlay])


def assert_resolved(index_config: object, index_class: type[IndexConfig]) -> None:
    assert type(index_config) is index_class
    assert isinstance(index_config, TezosHeadIndexConfig | TezosOperationsUnfilteredIndexConfig)
    assert index_config.callback == 'on_head'
    assert [h.callback for h in index_config.handlers] == ['on_head']
    assert [d.name for d in index_config.datasources] == ['tzkt_mainnet']


@pytest.mark.parametrize(('template', 'index_class'), TEMPLATES)
async def test_callback_template_yaml(tmp_path: Path, template: str, index_class: type[IndexConfig]) -> None:
    config = load_config(tmp_path, template + INDEX)
    config.initialize()

    assert_resolved(config.indexes['from_template'], index_class)


@pytest.mark.parametrize(('template', 'index_class'), TEMPLATES)
async def test_callback_template_add_index(tmp_path: Path, template: str, index_class: type[IndexConfig]) -> None:
    config = load_config(tmp_path, template)
    config.initialize()

    config.add_index(name='from_template', template='tpl', values=VALUES)

    assert_resolved(config.indexes['from_template'], index_class)
