import hashlib
import logging
import pickle
from typing import Optional

import aiohttp
from aiolimiter import AsyncLimiter
from fcache.cache import FileCache  # type: ignore

from dipdup.utils import http_request


class DatasourceRequestProxy:
    def __init__(self, cache: bool = False, ratelimiter: Optional[AsyncLimiter] = None) -> None:
        self._logger = logging.getLogger(__name__)
        self._cache = FileCache('dipdup', flag='cs') if cache else None
        self._ratelimiter = ratelimiter
        self._session = aiohttp.ClientSession()

    async def http_request(self, method: str, skip_cache: bool = False, weight: int = 1, **kwargs):
        if self._cache is not None and not skip_cache:
            key = hashlib.sha256(pickle.dumps([method, kwargs])).hexdigest()
            try:
                return self._cache[key]
            except KeyError:
                if self._ratelimiter:
                    await self._ratelimiter.acquire(weight)
                response = await http_request(
                    session=self._session,
                    method=method,
                    **kwargs,
                )
                self._cache[key] = response
                return response
        else:
            if self._ratelimiter:
                await self._ratelimiter.acquire(weight)
            response = await http_request(
                session=self._session,
                method=method,
                **kwargs,
            )
            return response

    async def close_session(self) -> None:
        await self._session.close()
