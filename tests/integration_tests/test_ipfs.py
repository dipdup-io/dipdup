from unittest import IsolatedAsyncioTestCase

from dipdup.config import DEFAULT_IPFS_URL
from dipdup.datasources.ipfs.datasource import IpfsDatasource


class IpfsDatasourceTest(IsolatedAsyncioTestCase):
    async def test_ipfs_datasource(self) -> None:
        ipfs = IpfsDatasource(DEFAULT_IPFS_URL, IpfsDatasource._default_http_config)
        async with ipfs:
            file = await ipfs.get('QmdCz7XGkBtd5DFmpDPDN3KFRmpkQHJsDgGiG16cgVbUYu')
            self.assertEqual(file[:4].decode()[1:], 'PDF')

            file = await ipfs.get('QmSgSC7geYH3Ae4SpUHy4KutxqNH9ESKBGXoCN4JQdbtEz/package.json')
            self.assertEqual(file['name'], 'json-buffer')
