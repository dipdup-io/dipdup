from pathlib import Path

from dipdup.config import HttpConfig
from dipdup.config.ipfs import DEFAULT_IPFS_URL
from dipdup.config.ipfs import IpfsDatasourceConfig
from dipdup.datasources.ipfs import IpfsDatasource


async def test_ipfs_datasource() -> None:
    config = IpfsDatasourceConfig(
        kind='ipfs',
        url=DEFAULT_IPFS_URL,
        http=HttpConfig(
            replay_path=str(Path(__file__).parent.parent / 'replays'),
        ),
    )
    config._name = 'ipfs'
    ipfs = IpfsDatasource(config)
    async with ipfs:
        file = await ipfs.get('bafybeifx7yeb55armcsxwwitkymga5xf53dxiarykms3ygqic223w5sk3m')
        assert file[:5].decode() == 'Hello'

        file = await ipfs.get('QmSgSC7geYH3Ae4SpUHy4KutxqNH9ESKBGXoCN4JQdbtEz/package.json')
        assert file['name'] == 'json-buffer'
