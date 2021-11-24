import asyncio
from os.path import dirname
from os.path import join

from dipdup.config import DipDupConfig
from dipdup.config import SqliteDatabaseConfig
from dipdup.dipdup import DipDup


async def main():
    config_path = join(dirname(__file__), 'quipuswap.yml')
    config = DipDupConfig.load([config_path])
    config.database = SqliteDatabaseConfig(kind='sqlite', path=':memory:')
    config.initialize()
    await DipDup(config).run()


asyncio.run(main())
