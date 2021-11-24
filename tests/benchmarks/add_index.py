import asyncio
import uuid

from dipdup.config import DipDupConfig
from dipdup.config import SqliteDatabaseConfig
from dipdup.dipdup import DipDup
from dipdup.utils.database import tortoise_wrapper

config = DipDupConfig.load(['tests/integration_tests/quipuswap.yml'])
config.database = SqliteDatabaseConfig(kind='sqlite', path=':memory:')
config.initialize()
dipdup = DipDup(config)

url = config.database.connection_string
models = f'{config.package}.models'


async def main():
    async with tortoise_wrapper(url, models):
        await dipdup._set_up_hooks()
        await dipdup._initialize_schema()
        await dipdup._create_datasources()

        for i in range(5000):
            address = 'KT' + str(uuid.uuid4())[:34]
            await dipdup._ctx.add_contract(
                name=str(i),
                address=address,
                typename='quipu_fa12',
            )
            await dipdup._ctx.add_index(
                name=str(i),
                template='quipuswap_fa12',
                values={
                    'dex_contract': str(i),
                    'token_contract': str(i),
                    'symbol': str(i),
                    'decimals': 0,
                },
            )


asyncio.run(main())
