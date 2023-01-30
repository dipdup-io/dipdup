import aiohttp

from dipdup.models.metadata import MetadataNetwork


async def test_metadata_networks() -> None:
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
                assert network['network'] in MetadataNetwork.__members__
