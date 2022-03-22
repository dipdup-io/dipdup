from contextlib import asynccontextmanager
from typing import AsyncIterator
from unittest import IsolatedAsyncioTestCase

from dipdup.config import HTTPConfig
from dipdup.datasources.tzkt.datasource import TzktDatasource

# from unittest import skip


@asynccontextmanager
async def with_tzkt(batch_size: int):
    config = HTTPConfig(batch_size=batch_size)
    datasource = TzktDatasource('https://api.tzkt.io', config)
    async with datasource:
        yield datasource


async def take_two(iterable: AsyncIterator):
    result = ()
    left = 2
    async for batch in iterable:
        result = result + batch
        left -= 1
        if not left:
            return result
    raise RuntimeError


class TzktDatasourceTest(IsolatedAsyncioTestCase):
    # @skip('')
    async def test_get_similar_contracts(self) -> None:
        async with with_tzkt(2) as tzkt:
            contracts = await tzkt.get_similar_contracts(
                address='KT1WBLrLE2vG8SedBqiSJFm4VVAZZBytJYHc',
                strict=False,
            )
            self.assertEqual(
                ('KT1W3VGRUjvS869r4ror8kdaxqJAZUbPyjMT', 'KT1K4EwTpbvYN9agJdjpyJm4ZZdhpUNKB3F6'),
                contracts,
            )

            contracts = await tzkt.get_similar_contracts(
                address='KT1WBLrLE2vG8SedBqiSJFm4VVAZZBytJYHc',
                strict=True,
            )
            self.assertEqual(
                ('KT1W3VGRUjvS869r4ror8kdaxqJAZUbPyjMT', 'KT1K4EwTpbvYN9agJdjpyJm4ZZdhpUNKB3F6'),
                contracts,
            )

    # @skip('')
    async def test_iter_similar_contracts(self):
        async with with_tzkt(1) as tzkt:
            contracts = await take_two(
                tzkt.iter_similar_contracts(
                    address='KT1WBLrLE2vG8SedBqiSJFm4VVAZZBytJYHc',
                    strict=False,
                )
            )
            self.assertEqual(
                ('KT1W3VGRUjvS869r4ror8kdaxqJAZUbPyjMT', 'KT1K4EwTpbvYN9agJdjpyJm4ZZdhpUNKB3F6'),
                contracts,
            )

            contracts = await take_two(
                tzkt.iter_similar_contracts(
                    address='KT1WBLrLE2vG8SedBqiSJFm4VVAZZBytJYHc',
                    strict=True,
                )
            )
            self.assertEqual(
                ('KT1W3VGRUjvS869r4ror8kdaxqJAZUbPyjMT', 'KT1K4EwTpbvYN9agJdjpyJm4ZZdhpUNKB3F6'),
                contracts,
            )

    # @skip('')
    async def test_get_originated_contracts(self) -> None:
        async with with_tzkt(2) as tzkt:
            contracts = await tzkt.get_originated_contracts(
                address='KT1Lw8hCoaBrHeTeMXbqHPG4sS4K1xn7yKcD',
            )
            self.assertEqual(
                'KT1X1LgNkQShpF9nRLYw3Dgdy4qp38MX617z',
                contracts[0]['address'],
            )
            self.assertEqual(
                'KT1BgezWwHBxA9NrczwK9x3zfgFnUkc7JJ4b',
                contracts[1]['address'],
            )

    # @skip('')
    async def iter_originated_contracts(self):
        async with with_tzkt(1) as tzkt:
            contracts = await take_two(
                tzkt.iter_originated_contracts(
                    address='KT1Lw8hCoaBrHeTeMXbqHPG4sS4K1xn7yKcD',
                )
            )
            self.assertEqual(
                'KT1X1LgNkQShpF9nRLYw3Dgdy4qp38MX617z',
                contracts[0]['address'],
            )
            self.assertEqual(
                'KT1BgezWwHBxA9NrczwK9x3zfgFnUkc7JJ4b',
                contracts[1]['address'],
            )

    # @skip('')
    async def test_get_contract_summary(self):
        async with with_tzkt(1) as tzkt:
            contract = await tzkt.get_contract_summary(
                address='KT1Lw8hCoaBrHeTeMXbqHPG4sS4K1xn7yKcD',
            )
            self.assertEqual(
                'KT1Lw8hCoaBrHeTeMXbqHPG4sS4K1xn7yKcD',
                contract['address'],
            )

    # @skip('')
    async def test_get_contract_storage(self):
        async with with_tzkt(1) as tzkt:
            storage = await tzkt.get_contract_storage(
                address='KT1Lw8hCoaBrHeTeMXbqHPG4sS4K1xn7yKcD',
            )
            self.assertEqual(
                1451,
                storage['token_lambdas'],
            )

    # @skip('')
    async def test_get_jsonschemas(self):
        async with with_tzkt(1) as tzkt:
            jsonschemas = await tzkt.get_jsonschemas(
                address='KT1Lw8hCoaBrHeTeMXbqHPG4sS4K1xn7yKcD',
            )
            self.assertEqual(
                'string',
                jsonschemas['storageSchema']['properties']['baker_validator']['type'],
            )

    # @skip('')
    async def test_get_big_map(self):
        async with with_tzkt(2) as tzkt:
            big_map_keys = await tzkt.get_big_map(
                big_map_id=55031,
                level=550310,
            )
            self.assertEqual(
                (12392933, 12393108),
                (big_map_keys[0]['id'], big_map_keys[1]['id']),
            )

    # @skip('')
    async def test_iter_big_map(self):
        async with with_tzkt(1) as tzkt:
            big_map_keys = await take_two(
                tzkt.iter_big_map(
                    big_map_id=55031,
                    level=550310,
                )
            )
            self.assertEqual(
                (12392933, 12393108),
                (big_map_keys[0]['id'], big_map_keys[1]['id']),
            )

    # @skip('')
    async def test_get_contract_big_maps(self):
        async with with_tzkt(2) as tzkt:
            big_maps = await tzkt.get_contract_big_maps(
                address='KT1Lw8hCoaBrHeTeMXbqHPG4sS4K1xn7yKcD',
            )
            self.assertEqual(
                ('votes', 'voters'),
                (big_maps[0]['path'], big_maps[1]['path']),
            )

    # @skip('')
    async def test_iter_contract_big_maps(self):
        async with with_tzkt(1) as tzkt:
            big_maps = await take_two(
                tzkt.iter_contract_big_maps(
                    address='KT1Lw8hCoaBrHeTeMXbqHPG4sS4K1xn7yKcD',
                )
            )
            self.assertEqual(
                ('votes', 'voters'),
                (big_maps[0]['path'], big_maps[1]['path']),
            )

    # @skip('')
    async def test_get_migration_originations(self):
        async with with_tzkt(2) as tzkt:
            originations = await tzkt.get_migration_originations()
            self.assertEqual(67955553, originations[0].id)
            self.assertEqual(67955554, originations[1].id)

    # @skip('')
    async def test_iter_migration_originations(self):
        async with with_tzkt(1) as tzkt:
            originations = await take_two(tzkt.iter_migration_originations())
            self.assertEqual(67955553, originations[0].id)
            self.assertEqual(67955554, originations[1].id)
