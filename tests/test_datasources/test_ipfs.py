from unittest import IsolatedAsyncioTestCase

from dipdup.config import DEFAULT_IPFS_URL
from dipdup.config import HTTPConfig
from dipdup.datasources.ipfs.datasource import IpfsDatasource


class IpfsDatasourceTest(IsolatedAsyncioTestCase):
    async def test_ipfs_datasource(self) -> None:
        ipfs = IpfsDatasource(
            url=DEFAULT_IPFS_URL,
            http_config=HTTPConfig(
                replay_path='~/.cache/dipdup/replays',
            ),
        )
        async with ipfs:
            file = await ipfs.get('bafybeifx7yeb55armcsxwwitkymga5xf53dxiarykms3ygqic223w5sk3m')
            self.assertEqual(file[:5].decode(), 'Hello')

            file = await ipfs.get('QmSgSC7geYH3Ae4SpUHy4KutxqNH9ESKBGXoCN4JQdbtEz/package.json')
            self.assertEqual(file['name'], 'json-buffer')
