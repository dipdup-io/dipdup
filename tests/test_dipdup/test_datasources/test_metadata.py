from unittest import IsolatedAsyncioTestCase

import aiohttp

from dipdup.datasources.metadata.enums import MetadataNetwork


class MetadataDatasourceTest(IsolatedAsyncioTestCase):
    async def test_metadata_networks(self) -> None:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                'https://metadata.dipdup.net/v1/graphql',
                json={
                    'query': 'query MetadataNetworks { contract_metadata(distinct_on: network) { network } }',
                    'operationName': 'MetadataNetworks',
                },
            ) as response:
                res = await response.json()
                for network in res['data']['contract_metadata']:
                    self.assertIn(network['network'], MetadataNetwork.__members__)
