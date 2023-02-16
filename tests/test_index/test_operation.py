from typing import AsyncIterator
from typing import cast

import pytest

from dipdup.config import DipDupConfig
from dipdup.config.tezos_tzkt_operations import OperationsHandlerOriginationPatternConfig
from dipdup.config.tezos_tzkt_operations import TzktOperationsHandlerConfig
from dipdup.config.tezos_tzkt_operations import TzktOperationsIndexConfig
from dipdup.datasources.tezos_tzkt import TzktDatasource
from dipdup.indexes.tezos_tzkt_operations.fetcher import get_origination_filters
from dipdup.indexes.tezos_tzkt_operations.fetcher import get_transaction_filters
from tests import CONFIGS_PATH
from tests import tzkt_replay


@pytest.fixture
async def tzkt() -> AsyncIterator[TzktDatasource]:
    async with tzkt_replay() as tzkt:
        yield tzkt


@pytest.fixture
def index_config() -> TzktOperationsIndexConfig:
    config = DipDupConfig.load([CONFIGS_PATH / 'operation_filters.yml'], True)
    config.initialize()
    return cast(TzktOperationsIndexConfig, config.indexes['test'])


async def test_ignored_type_filter(
    tzkt: TzktDatasource,
    index_config: TzktOperationsIndexConfig,
) -> None:
    index_config.types = ()
    addresses, hashes = await get_origination_filters(index_config, tzkt)
    assert not addresses
    assert not hashes

    addresses, hashes = await get_transaction_filters(index_config, tzkt)
    assert not addresses
    assert not hashes


async def test_get_origination_filters(
    tzkt: TzktDatasource,
    index_config: TzktOperationsIndexConfig,
) -> None:
    index_config.handlers = (
        TzktOperationsHandlerConfig(
            'address_origination',
            (
                OperationsHandlerOriginationPatternConfig(
                    originated_contract=index_config.contracts[0],
                ),
            ),
        ),
    )
    addresses, hashes = await get_origination_filters(index_config, tzkt)
    assert addresses == {'KT1RJ6PbjHpwc3M5rw5s2Nbmefwbuwbdxton'}
    assert not hashes

    index_config.handlers = (
        TzktOperationsHandlerConfig(
            'hash_origination',
            (
                OperationsHandlerOriginationPatternConfig(
                    originated_contract=index_config.contracts[1],
                ),
            ),
        ),
    )
    addresses, hashes = await get_origination_filters(index_config, tzkt)
    assert not addresses
    assert hashes == {-1585533315}

    index_config.handlers = (
        TzktOperationsHandlerConfig(
            'hash_address_origination',
            (
                OperationsHandlerOriginationPatternConfig(
                    originated_contract=index_config.contracts[2],
                ),
            ),
        ),
    )
    addresses, hashes = await get_origination_filters(index_config, tzkt)
    assert not addresses
    assert hashes == {-680664524}

    index_config.handlers = (
        TzktOperationsHandlerConfig(
            'address_source',
            (
                OperationsHandlerOriginationPatternConfig(
                    source=index_config.contracts[0],
                ),
            ),
        ),
    )
    addresses, hashes = await get_origination_filters(index_config, tzkt)
    assert not addresses
    assert hashes == set()


# async def test_get_transaction_filters(tzkt: TzktDatasource, index_config: TzktOperationsIndexConfig) -> None:
#     index_config.types = (TzktOperationType.transaction,)
#     addresses, hashes = await get_transaction_filters(index_config, tzkt)
#     assert filters == ({'KT1RJ6PbjHpwc3M5rw5s2Nbmefwbuwbdxton'}, {-680664524, -1585533315})

#     index_config.types = ()
#     addresses, hashes = await get_transaction_filters(index_config, tzkt)
#     assert filters == (set(), set())
