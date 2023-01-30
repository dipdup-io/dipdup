from pathlib import Path

from dipdup.config import DEFAULT_IPFS_URL
from dipdup.config import HTTPConfig
from dipdup.datasources.ipfs import IpfsDatasource


async def test_ipfs_datasource() -> None:
    ipfs = IpfsDatasource(
        url=DEFAULT_IPFS_URL,
        http_config=HTTPConfig(
            replay_path=str(Path(__file__).parent.parent / 'replays'),
        ),
    )
    async with ipfs:
        file = await ipfs.get('bafybeifx7yeb55armcsxwwitkymga5xf53dxiarykms3ygqic223w5sk3m')
        assert file[:5].decode() == 'Hello'

        file = await ipfs.get('QmSgSC7geYH3Ae4SpUHy4KutxqNH9ESKBGXoCN4JQdbtEz/package.json')
        assert file['name'] == 'json-buffer'
