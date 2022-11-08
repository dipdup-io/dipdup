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
            file = await ipfs.get('QmdCz7XGkBtd5DFmpDPDN3KFRmpkQHJsDgGiG16cgVbUYu')
            self.assertEqual(file[:4].decode()[1:], 'PDF')

            file = await ipfs.get('QmSgSC7geYH3Ae4SpUHy4KutxqNH9ESKBGXoCN4JQdbtEz/package.json')
            self.assertEqual(file['name'], 'json-buffer')
