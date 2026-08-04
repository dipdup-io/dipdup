import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from dipdup import env
from dipdup.config import HttpConfig
from dipdup.config.tezos_tzkt import TezosTzktDatasourceConfig
from dipdup.datasources.tezos_tzkt import TezosTzktDatasource

env.set_test()


TEST_CONFIGS = Path(__file__).parent / 'configs'

REPO_ROOT = Path(__file__).parent.parent


def has_api_keys(*names: str) -> bool:
    """Check that every API key is set to a non-empty value.

    NOTE: GitHub exposes secrets unavailable to the job (e.g. on fork pull requests) as empty strings,
    NOTE: so a bare presence check would send guarded tests to the network without credentials.
    """
    return all(os.environ.get(name) for name in names)


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
