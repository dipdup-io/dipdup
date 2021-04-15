from contextlib import asynccontextmanager
from typing import Optional

import aiohttp
from tortoise import Tortoise

from dipdup import __version__


@asynccontextmanager
async def tortoise_wrapper(url: str, models: Optional[str] = None):
    try:
        modules = {'int_models': ['dipdup.models']}
        if models:
            modules['models'] = [models]
        await Tortoise.init(
            db_url=url,
            modules=modules,  # type: ignore
        )
        yield
    finally:
        await Tortoise.close_connections()


@asynccontextmanager
async def http_request(method: str, **kwargs):
    async with aiohttp.ClientSession() as session:
        headers = {
            **kwargs.pop('headers', {}),
            'User-Agent': f'dupdup/{__version__}',
        }
        async with getattr(session, method)(
            skip_auto_headers={'User-Agent'},
            headers=headers,
            **kwargs,
        ) as response:
            yield response
