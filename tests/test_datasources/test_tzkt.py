from collections.abc import AsyncIterator
from pathlib import Path
from typing import TypeVar
from unittest.mock import AsyncMock

import orjson as json
import pysignalr.exceptions
import pytest

from dipdup.exceptions import DatasourceError
from dipdup.exceptions import FrameworkException
from dipdup.exceptions import InvalidRequestError
from dipdup.models.tezos_tzkt import HeadSubscription
from dipdup.models.tezos_tzkt import TzktMessageType
from dipdup.models.tezos_tzkt import TzktOperationData
from tests import tzkt_replay

T = TypeVar('T')


async def take_two(iterable: AsyncIterator[tuple[T, ...]]) -> tuple[T, ...]:
    result: tuple[T, ...] = ()
    left = 2
    async for batch in iterable:
        result = result + batch
        left -= 1
        if not left:
            return result
    raise FrameworkException('Not enough items in iterable')


async def test_get_similar_contracts() -> None:
    async with tzkt_replay(batch_size=2) as tzkt:
        contracts = await tzkt.get_similar_contracts(
            address='KT1WBLrLE2vG8SedBqiSJFm4VVAZZBytJYHc',
            strict=False,
        )
        assert (contracts[0]['address'], contracts[1]['address']) == (
            'KT1W3VGRUjvS869r4ror8kdaxqJAZUbPyjMT',
            'KT1K4EwTpbvYN9agJdjpyJm4ZZdhpUNKB3F6',
        )

        contracts = await tzkt.get_similar_contracts(
            address='KT1WBLrLE2vG8SedBqiSJFm4VVAZZBytJYHc',
            strict=True,
        )
        assert (contracts[0]['address'], contracts[1]['address']) == (
            'KT1W3VGRUjvS869r4ror8kdaxqJAZUbPyjMT',
            'KT1K4EwTpbvYN9agJdjpyJm4ZZdhpUNKB3F6',
        )


async def test_iter_similar_contracts() -> None:
    async with tzkt_replay(batch_size=1) as tzkt:
        contracts = await take_two(
            tzkt.iter_similar_contracts(
                address='KT1WBLrLE2vG8SedBqiSJFm4VVAZZBytJYHc',
                strict=False,
            )
        )
        assert (contracts[0]['address'], contracts[1]['address']) == (
            'KT1W3VGRUjvS869r4ror8kdaxqJAZUbPyjMT',
            'KT1K4EwTpbvYN9agJdjpyJm4ZZdhpUNKB3F6',
        )

        contracts = await take_two(
            tzkt.iter_similar_contracts(
                address='KT1WBLrLE2vG8SedBqiSJFm4VVAZZBytJYHc',
                strict=True,
            )
        )
        assert (contracts[0]['address'], contracts[1]['address']) == (
            'KT1W3VGRUjvS869r4ror8kdaxqJAZUbPyjMT',
            'KT1K4EwTpbvYN9agJdjpyJm4ZZdhpUNKB3F6',
        )


async def test_get_originated_contracts() -> None:
    async with tzkt_replay(batch_size=2) as tzkt:
        contracts = await tzkt.get_originated_contracts(
            address='KT1Lw8hCoaBrHeTeMXbqHPG4sS4K1xn7yKcD',
        )
        assert contracts[0]['address'] == 'KT1W3VGRUjvS869r4ror8kdaxqJAZUbPyjMT'
        assert contracts[1]['address'] == 'KT1K4EwTpbvYN9agJdjpyJm4ZZdhpUNKB3F6'


async def iter_originated_contracts() -> None:
    async with tzkt_replay(batch_size=1) as tzkt:
        contracts = await take_two(
            tzkt.iter_originated_contracts(
                address='KT1Lw8hCoaBrHeTeMXbqHPG4sS4K1xn7yKcD',
            )
        )
        assert contracts[0]['address'] == 'KT1X1LgNkQShpF9nRLYw3Dgdy4qp38MX617z'
        assert contracts[1]['address'] == 'KT1BgezWwHBxA9NrczwK9x3zfgFnUkc7JJ4b'


async def test_get_contract_summary() -> None:
    async with tzkt_replay(batch_size=1) as tzkt:
        contract = await tzkt.get_contract_summary(
            address='KT1Lw8hCoaBrHeTeMXbqHPG4sS4K1xn7yKcD',
        )
        assert contract['address'] == 'KT1Lw8hCoaBrHeTeMXbqHPG4sS4K1xn7yKcD'


async def test_get_contract_hashes() -> None:
    async with tzkt_replay(batch_size=1) as tzkt:
        code_hash, type_hash = await tzkt.get_contract_hashes(
            address='KT1Lw8hCoaBrHeTeMXbqHPG4sS4K1xn7yKcD',
        )
        assert code_hash == -517093702
        assert type_hash == 1479913559


async def test_get_contract_storage() -> None:
    async with tzkt_replay(batch_size=1) as tzkt:
        storage = await tzkt.get_contract_storage(
            address='KT1Lw8hCoaBrHeTeMXbqHPG4sS4K1xn7yKcD',
        )
        assert storage['token_lambdas'] == 1451


async def test_get_jsonschemas() -> None:
    async with tzkt_replay(batch_size=1) as tzkt:
        jsonschemas = await tzkt.get_jsonschemas(
            address='KT1Lw8hCoaBrHeTeMXbqHPG4sS4K1xn7yKcD',
        )
        assert jsonschemas['storageSchema']['properties']['baker_validator']['type'] == 'string'


async def test_get_big_map() -> None:
    async with tzkt_replay(batch_size=2) as tzkt:
        big_map_keys = await tzkt.get_big_map(
            big_map_id=55031,
            level=550310,
        )
        assert (big_map_keys[0]['id'], big_map_keys[1]['id']) == (12392933, 12393108)


async def test_iter_big_map() -> None:
    async with tzkt_replay(batch_size=1) as tzkt:
        big_map_keys = await take_two(
            tzkt.iter_big_map(
                big_map_id=55031,
                level=550310,
            )
        )
        assert (big_map_keys[0]['id'], big_map_keys[1]['id']) == (12392933, 12393108)


async def test_get_contract_big_maps() -> None:
    async with tzkt_replay(batch_size=2) as tzkt:
        big_maps = await tzkt.get_contract_big_maps(
            address='KT1Lw8hCoaBrHeTeMXbqHPG4sS4K1xn7yKcD',
        )
        assert (big_maps[0]['path'], big_maps[1]['path']) == ('votes', 'voters')


async def test_iter_contract_big_maps() -> None:
    async with tzkt_replay(batch_size=1) as tzkt:
        big_maps = await take_two(
            tzkt.iter_contract_big_maps(
                address='KT1Lw8hCoaBrHeTeMXbqHPG4sS4K1xn7yKcD',
            )
        )
        assert (big_maps[0]['path'], big_maps[1]['path']) == ('votes', 'voters')


async def test_get_migration_originations() -> None:
    async with tzkt_replay(batch_size=2) as tzkt:
        originations = await tzkt.get_migration_originations()
        assert originations[0].id == 66864948445184
        assert originations[1].id == 66864949493760


async def test_iter_migration_originations() -> None:
    async with tzkt_replay(batch_size=1) as tzkt:
        originations = await take_two(tzkt.iter_migration_originations())
        assert originations[0].id == 66864948445184
        assert originations[1].id == 66864949493760


async def test_get_originations() -> None:
    async with tzkt_replay(batch_size=1) as tzkt:
        originations = await tzkt.get_originations(
            addresses={'KT1PWx2mnDueood7fEmfbBDKx1D9BAnnXitn'},
            first_level=889027,
            last_level=889027,
        )
        assert originations[0].id == 24969533718528
        assert originations[0].originated_contract_tzips == ('fa12',)


async def test_on_operation_message_data() -> None:
    json_path = Path(__file__).parent.parent / 'responses' / 'ftzfun.json'
    operations_json = json.loads(json_path.read_text())

    message = {'type': 1, 'state': 2, 'data': operations_json}
    async with tzkt_replay(batch_size=1) as tzkt:
        emit_mock = AsyncMock()
        tzkt.call_on_operations(emit_mock)
        tzkt._subscriptions.add(HeadSubscription())
        tzkt.set_sync_level(HeadSubscription(), 1)

        level = tzkt.get_channel_level(TzktMessageType.operation)
        assert level == 1

        await tzkt._on_message(TzktMessageType.operation, [message])

        level = tzkt.get_channel_level(TzktMessageType.operation)
        assert level == 2
        assert isinstance(emit_mock.await_args_list[0][0][1][0], TzktOperationData)


# FIXME: Hangs without internet
async def test_no_content() -> None:
    async with tzkt_replay('https://api.ghostnet.tzkt.io', batch_size=1) as tzkt:
        with pytest.raises(InvalidRequestError):
            await tzkt.get_jsonschemas('KT1EHdK9asB6BtPLvt1ipKRuxsrKoQhDoKgs')


async def test_signalr_client() -> None:
    fail_mock = AsyncMock(side_effect=pysignalr.exceptions.ConnectionError(418))

    async with tzkt_replay(batch_size=1) as tzkt:
        tzkt._http_config.retry_sleep = 0
        signalr_client = tzkt._get_signalr_client()
        signalr_client.run = fail_mock  # type: ignore[method-assign]

        with pytest.raises(DatasourceError):
            await tzkt.run()
        assert fail_mock.call_count == tzkt._http_config.retry_count
