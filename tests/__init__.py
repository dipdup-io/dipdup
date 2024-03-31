from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from dipdup import env
from dipdup.config import HttpConfig
from dipdup.config.tezos_tzkt import TezosTzktDatasourceConfig
from dipdup.datasources.tezos_tzkt import TezosTzktDatasource

env.set_test()


TEST_CONFIGS = Path(__file__).parent / 'configs'


@asynccontextmanager
async def tzkt_replay(
    url: str = 'https://api.tzkt.io',
    batch_size: int | None = None,
) -> AsyncIterator[TezosTzktDatasource]:
    http_config = HttpConfig(
        batch_size=batch_size,
        replay_path=str(Path(__file__).parent / 'replays'),
    )
    config = TezosTzktDatasourceConfig(
        kind='tezos.tzkt',
        url=url,
        http=http_config,
    )
    config._name = 'tzkt'
    datasource = TezosTzktDatasource(config)
    async with datasource:
        yield datasource
