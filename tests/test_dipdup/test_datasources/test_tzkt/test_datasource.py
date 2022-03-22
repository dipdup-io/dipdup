from typing import AsyncIterator
from unittest import IsolatedAsyncioTestCase

from dipdup.config import HTTPConfig
from dipdup.datasources.tzkt.datasource import TzktDatasource
from unittest import skip

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
    @skip('')
    async def test_get_similar_contracts(self) -> None:
        tzkt = TzktDatasource(
            url='https://api.tzkt.io',
            http_config=HTTPConfig(batch_size=2),
        )

        async with tzkt:
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

    @skip('')
    async def test_iter_similar_contracts(self):
        tzkt = TzktDatasource(
            url='https://api.tzkt.io',
            http_config=HTTPConfig(batch_size=1),
        )

        async with tzkt:
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

    @skip('')
    async def test_get_originated_contracts(self) -> None:
        tzkt = TzktDatasource(
            url='https://api.tzkt.io',
            http_config=HTTPConfig(batch_size=2),
        )

        async with tzkt:
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

    @skip('')
    async def iter_originated_contracts(self):
        tzkt = TzktDatasource(
            url='https://api.tzkt.io',
            http_config=HTTPConfig(batch_size=1),
        )

        async with tzkt:
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
