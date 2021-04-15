from contextlib import asynccontextmanager
from typing import Optional

from tortoise import Tortoise


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
