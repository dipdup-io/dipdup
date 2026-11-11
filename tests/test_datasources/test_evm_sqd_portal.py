from typing import cast
from unittest.mock import AsyncMock

import orjson
from pydantic import TypeAdapter

from dipdup.config import DatasourceConfigU
from dipdup.config.evm_sqd_portal import EvmPortalDatasourceConfig
from dipdup.config.evm_subsquid import EvmSubsquidDatasourceConfig
from dipdup.datasources import create_datasource
from dipdup.datasources.evm_sqd_portal import EvmPortalDatasource
from dipdup.datasources.evm_subsquid import EvmSubsquidDatasource
from dipdup.datasources.evm_subsquid import _AbstractEvmSubsquidDatasource
from dipdup.models.evm_subsquid import Query


def _parse_datasource(raw: dict[str, object]) -> object:
    return TypeAdapter(DatasourceConfigU).validate_python(raw)


def _portal_config(url: str = 'https://portal.sqd.dev/datasets/ethereum-mainnet') -> EvmPortalDatasourceConfig:
    config = EvmPortalDatasourceConfig(kind='evm.sqd_portal', url=url)
    config._name = 'portal'
    return config


def _portal_datasource() -> EvmPortalDatasource:
    return EvmPortalDatasource(_portal_config())


def test_config_parses_sqd_portal_kind() -> None:
    config = _parse_datasource(
        {
            'kind': 'evm.sqd_portal',
            'url': 'https://portal.sqd.dev/datasets/ethereum-mainnet',
        },
    )
    assert isinstance(config, EvmPortalDatasourceConfig)
    assert config.url == 'https://portal.sqd.dev/datasets/ethereum-mainnet'
    # NOTE: api_key is optional (not required for the public Portal)
    assert config.api_key is None
    # NOTE: Portal finalized stream — data is always finalized, like v2.archive
    assert config.rollback_depth == 0


def test_create_datasource_builds_portal() -> None:
    datasource = create_datasource(_portal_config())
    # NOTE: Concrete Portal datasource, not abstract — MRO must resolve transport
    assert isinstance(datasource, EvmPortalDatasource)
    # NOTE: Shares the EVM chain logic base, so index filters catch it as a subsquid-like source
    assert isinstance(datasource, _AbstractEvmSubsquidDatasource)


async def test_get_head_level_returns_number() -> None:
    datasource = _portal_datasource()
    datasource.request = AsyncMock(return_value={'number': 21_000_000, 'hash': '0xabc'})  # type: ignore[method-assign]

    level = await datasource.get_head_level()

    assert level == 21_000_000
    # NOTE: Portal exposes the finalized head at `/finalized-head`, not v2.archive's `/height`
    method, url = datasource.request.call_args.args
    assert (method, url) == ('get', 'finalized-head')


async def test_query_worker_parses_ndjson_bytes() -> None:
    datasource = _portal_datasource()
    block_1 = {'header': {'number': 100}, 'logs': []}
    block_2 = {'header': {'number': 101}, 'logs': []}
    # NOTE: Multi-line NDJSON comes back from `request()` as raw bytes, one block per line
    ndjson = orjson.dumps(block_1) + b'\n' + orjson.dumps(block_2)
    datasource.request = AsyncMock(return_value=ndjson)  # type: ignore[method-assign]

    query = cast('Query', {'logs': [], 'fields': {}, 'fromBlock': 100, 'toBlock': 101})
    blocks = await datasource.query_worker(query, current_level=100)

    assert blocks == [block_1, block_2]
    method, url = datasource.request.call_args.args
    assert (method, url) == ('post', 'finalized-stream')


async def test_query_worker_injects_evm_type() -> None:
    datasource = _portal_datasource()
    datasource.request = AsyncMock(return_value=b'')  # type: ignore[method-assign]

    query = cast('Query', {'logs': [], 'fromBlock': 0, 'toBlock': 0})
    await datasource.query_worker(query, current_level=0)

    # NOTE: EVM queries omit `type`; Portal requires it, so the datasource injects it
    sent = datasource.request.call_args.kwargs['json']
    assert sent['type'] == 'evm'
    # NOTE: the caller's query dict must not be mutated
    assert 'type' not in query


async def test_query_worker_single_dict_block() -> None:
    datasource = _portal_datasource()
    block = {'header': {'number': 100}, 'logs': []}
    # NOTE: a single-line stream parses straight to a dict, not bytes
    datasource.request = AsyncMock(return_value=block)  # type: ignore[method-assign]

    query = cast('Query', {'logs': [], 'fromBlock': 100, 'toBlock': 100})
    blocks = await datasource.query_worker(query, current_level=100)

    assert blocks == [block]


def test_archive_datasource_still_built() -> None:
    config = EvmSubsquidDatasourceConfig(
        kind='evm.subsquid',
        url='https://v2.archive.subsquid.io/network/ethereum-mainnet',
    )
    config._name = 'subsquid'
    datasource = create_datasource(config)

    # NOTE: v2.archive sibling is untouched by the refactor...
    assert isinstance(datasource, EvmSubsquidDatasource)
    # NOTE: ...and is matched by the same shared base the index filter now keys on
    assert isinstance(datasource, _AbstractEvmSubsquidDatasource)
