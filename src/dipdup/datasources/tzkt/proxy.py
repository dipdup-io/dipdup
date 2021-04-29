import hashlib
import logging
import pickle

from fcache.cache import FileCache  # type: ignore

from dipdup.utils import http_request


class TzktRequestProxy:
    def __init__(self, cache: bool = False) -> None:
        self._logger = logging.getLogger(__name__)
        self._cache = FileCache('dipdup', flag='cs') if cache else None

    async def http_request(self, method: str, skip_cache: bool = False, **kwargs):
        if self._cache is not None and not skip_cache:
            key = hashlib.sha256(pickle.dumps([method, kwargs])).hexdigest()
            try:
                return self._cache[key]
            except KeyError:
                response = await http_request(method, **kwargs)
                self._cache[key] = response
                return response
        else:
            response = await http_request(method, **kwargs)
            return response
