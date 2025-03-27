import logging
import time
from pathlib import Path
from typing import TypedDict
from typing import cast

from appdirs import user_cache_dir  # type: ignore[import-untyped]

from dipdup import __editable__
from dipdup import __version__

PREVIEW_MSG = 'You are running a pre-release version of DipDup. Please, report any issues to the GitHub repository.'
OUTDATED_MSG = 'You are running DipDup %s, while %s is available. Please run `dipdup self update` to upgrade.'
SKIP_MSG = 'Set `DIPDUP_NO_VERSION_CHECK` variable to hide this message.'
RELEASES_URL = 'https://api.github.com/repos/dipdup-io/dipdup/releases/latest'
CACHE_TTL = 24 * 60 * 60
CACHE_PATH = Path(user_cache_dir('dipdup')) / 'version_info.json'


_logger = logging.getLogger('dipdup.cli')


class CachedVersion(TypedDict):
    latest_version: str
    installed_version: str


async def check_version() -> None:
    if __editable__:
        return

    if not all(c.isdigit() or c == '.' for c in __version__):
        _logger.warning(PREVIEW_MSG)
        _logger.info(SKIP_MSG)
        return

    latest_version = _read_cached_version()
    if not latest_version:
        latest_version = await _get_latest_version()
        if latest_version:
            _write_cached_version(latest_version)
    if not latest_version:
        return

    if __version__ >= latest_version:
        return

    _logger.warning(
        OUTDATED_MSG,
        __version__,
        latest_version,
    )
    _logger.info(SKIP_MSG)


async def _get_latest_version() -> str | None:
    from contextlib import AsyncExitStack

    import aiohttp

    async with AsyncExitStack() as stack:
        session = await stack.enter_async_context(aiohttp.ClientSession())
        try:
            response = await session.get(RELEASES_URL)
            response_json = await response.json()
            return cast('str', response_json['tag_name'])
        except Exception as e:
            _logger.debug('Failed to get the latest version from GitHub: %s', e)
    return None


def _read_cached_version() -> str | None:
    if not CACHE_PATH.exists():
        return None

    if (time.time() - CACHE_PATH.stat().st_mtime) >= CACHE_TTL:
        CACHE_PATH.unlink()
        return None

    import orjson as json

    try:
        cached_version = cast(
            'CachedVersion',
            json.loads(CACHE_PATH.read_bytes()),
        )
        # NOTE: Invalidate cache if installed version is different
        if cached_version['installed_version'] == __version__:
            return cached_version['latest_version']
    except Exception as e:
        _logger.warning('Failed to read cache file %s: %s', CACHE_PATH, e)

    return None


def _write_cached_version(latest_version: str) -> None:
    from dipdup.utils import json_dumps
    from dipdup.utils import write

    version_info: CachedVersion = {
        'latest_version': latest_version,
        'installed_version': __version__,
    }

    try:
        write(CACHE_PATH, json_dumps(version_info), overwrite=True, silent=True)
    except Exception as e:
        _logger.warning('Failed to write cache file %s: %s', CACHE_PATH, e)
