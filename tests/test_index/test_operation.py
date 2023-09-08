from collections.abc import AsyncIterator
from contextlib import AsyncExitStack
from typing import cast

import pytest

from dipdup.config import DipDupConfig
from dipdup.config.tezos_tzkt_operations import OperationsHandlerOriginationPatternConfig
from dipdup.config.tezos_tzkt_operations import TzktOperationsHandlerConfig
from dipdup.config.tezos_tzkt_operations import TzktOperationsIndexConfig
from dipdup.datasources.tezos_tzkt import TzktDatasource
from dipdup.exceptions import FrameworkException
from dipdup.indexes.tezos_tzkt_operations.fetcher import get_origination_filters
from dipdup.indexes.tezos_tzkt_operations.fetcher import get_transaction_filters
from dipdup.models.tezos_tzkt import HeadSubscription
from dipdup.models.tezos_tzkt import TransactionSubscription
from dipdup.models.tezos_tzkt import TzktOperationType
from dipdup.test import create_dummy_dipdup
from dipdup.test import spawn_index
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


async def test_get_transaction_filters(tzkt: TzktDatasource, index_config: TzktOperationsIndexConfig) -> None:
    index_config.types = (TzktOperationType.transaction,)
    filters = await get_transaction_filters(index_config, tzkt)
    assert filters == ({'KT1RJ6PbjHpwc3M5rw5s2Nbmefwbuwbdxton'}, {-680664524, -1585533315})

    index_config.types = ()
    filters = await get_transaction_filters(index_config, tzkt)
    assert filters == (set(), set())


async def test_get_sync_level() -> None:
    config = DipDupConfig.load([CONFIGS_PATH / 'demo_token.yml'], True)
    async with AsyncExitStack() as stack:
        dipdup = await create_dummy_dipdup(config, stack)
        index = await spawn_index(dipdup, 'tzbtc_holders_mainnet')

        with pytest.raises(FrameworkException):
            index.get_sync_level()

        index.datasource.set_sync_level(None, 0)
        assert index.get_sync_level() == 0

        subs = index._config.get_subscriptions()
        assert subs == {
            HeadSubscription(),
            TransactionSubscription(address='KT1PWx2mnDueood7fEmfbBDKx1D9BAnnXitn'),
        }

        for i, sub in enumerate(subs):
            index.datasource.set_sync_level(sub, i + 1)
            assert index.get_sync_level() == i + 1
