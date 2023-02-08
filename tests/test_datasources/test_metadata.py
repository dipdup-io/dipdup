import aiohttp

from dipdup.models.tzip_metadata import TzipMetadataNetwork


async def test_metadata_networks() -> None:
    async with aiohttp.ClientSession() as session:
        async with session.post(
            'https://metadata.dipdup.net/v1/graphql',
            json={
                'query': 'query TzipMetadataNetworks { contract_metadata(distinct_on: network) { network } }',
                'operationName': 'TzipMetadataNetworks',
            },
        ) as response:
            res = await response.json()
            for network in res['data']['contract_metadata']:
                assert network['network'] in TzipMetadataNetwork.__members__
