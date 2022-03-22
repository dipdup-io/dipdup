from typing import AsyncIterator
from unittest import IsolatedAsyncioTestCase

from dipdup.config import HTTPConfig
from dipdup.datasources.tzkt.datasource import TzktDatasource


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
