
from typing import AsyncIterator, cast
import pytest
from dipdup.config import DipDupConfig, OperationHandlerConfig, OperationHandlerOriginationPatternConfig, OperationIndexConfig
from dipdup.datasources.datasource import Datasource
from dipdup.enums import OperationType
from dipdup.exceptions import FrameworkException
from dipdup.indexes.operation.fetcher import get_origination_filters, get_transaction_filters
from tests import CONFIGS_PATH
from tests import tzkt_replay


@pytest.fixture
async def tzkt() -> AsyncIterator[Datasource]:
    async with tzkt_replay() as tzkt:
        yield tzkt


@pytest.fixture
def index_config() -> OperationIndexConfig:
    config = DipDupConfig.load([CONFIGS_PATH / 'operation_filters.yml'], True)
    config.initialize()
    return cast(OperationIndexConfig, config.indexes['test'])


async def test_ignored_type_filter(
    tzkt: Datasource,
    index_config: OperationIndexConfig,
) -> None:
    index_config.types = ()
    addresses, hashes = await get_origination_filters(index_config, tzkt)  # type: ignore[arg-type]
    assert not addresses
    assert not hashes

    addresses, hashes = await get_transaction_filters(index_config, tzkt)  # type: ignore[arg-type]
    assert not addresses
    assert not hashes


async def test_get_origination_filters(
    tzkt: Datasource,
    index_config: OperationIndexConfig,
) -> None:
    index_config.handlers = (
        OperationHandlerConfig(
            'address_origination',
            (
                OperationHandlerOriginationPatternConfig(
                    originated_contract=index_config.contracts[0],
                ),
            ),
        ),
    )
    addresses, hashes = await get_origination_filters(index_config, tzkt)
    assert addresses == {'KT1RJ6PbjHpwc3M5rw5s2Nbmefwbuwbdxton'}
    assert not hashes

    index_config.handlers = (
        OperationHandlerConfig(
            'hash_origination',
            (
                OperationHandlerOriginationPatternConfig(
                    originated_contract=index_config.contracts[1],
                ),
            ),
        ),
    )
    addresses, hashes = await get_origination_filters(index_config, tzkt)
    assert not addresses
    assert hashes == {-1585533315}

    index_config.handlers = (
        OperationHandlerConfig(
            'hash_address_origination',
            (
                OperationHandlerOriginationPatternConfig(
                    originated_contract=index_config.contracts[2],
                ),
            ),
        ),
    )
    # NOTE: Resolved earlier
    with pytest.raises(FrameworkException):
        await get_origination_filters(index_config, tzkt)

    index_config.handlers = (
        OperationHandlerConfig(
            'address_source',
            (
                OperationHandlerOriginationPatternConfig(
                    source=index_config.contracts[0],
                ),
            ),
        ),
    )
    addresses, hashes = await get_origination_filters(index_config, tzkt)
    assert not addresses
    assert hashes == set()


async def test_get_transaction_filters(tzkt: Datasource, index_config: OperationIndexConfig) -> None:
    index_config.types = (OperationType.transaction,)
    index_config.contracts[2].code_hash = -680664524

    filters = await get_transaction_filters(index_config, tzkt)
    assert filters == ({'KT1RJ6PbjHpwc3M5rw5s2Nbmefwbuwbdxton'}, {-680664524, -1585533315})

    index_config.types = ()
    filters = await get_transaction_filters(index_config, tzkt)
    assert filters == (set(), set())
