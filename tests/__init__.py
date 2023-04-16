from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from dipdup import env
from dipdup.config import HttpConfig
from dipdup.config.tezos_tzkt import TzktDatasourceConfig
from dipdup.datasources.tezos_tzkt import TzktDatasource

env.set_test()


CONFIGS_PATH = Path(__file__).parent / 'configs'
REPLAYS_PATH = Path(__file__).parent / 'replays'
SRC_PATH = Path(__file__).parent.parent / 'src'


@asynccontextmanager
async def tzkt_replay(
    url: str = 'https://api.tzkt.io',
    batch_size: int | None = None,
) -> AsyncIterator[TzktDatasource]:
    http_config = HttpConfig(
        batch_size=batch_size,
        replay_path=str(Path(__file__).parent / 'replays'),
    )
    config = TzktDatasourceConfig(
        kind='tezos.tzkt',
        url=url,
        http=http_config,
    )
    config._name = 'tzkt'
    datasource = TzktDatasource(config)
    async with datasource:
        yield datasource
