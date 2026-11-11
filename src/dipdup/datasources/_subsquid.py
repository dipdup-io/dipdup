import asyncio
from abc import abstractmethod
from copy import copy
from typing import Any
from typing import Generic
from typing import TypeVar
from typing import cast

import orjson

from dipdup.config import HttpConfig
from dipdup.config._subsquid import SubsquidDatasourceConfig
from dipdup.datasources import Datasource
from dipdup.datasources import IndexDatasource
from dipdup.exceptions import DatasourceError
from dipdup.exceptions import FrameworkException
from dipdup.http import safe_exceptions
from dipdup.models import Head
from dipdup.models._subsquid import AbstractSubsquidQuery
from dipdup.sys import fire_and_forget

QueryT = TypeVar('QueryT', bound=AbstractSubsquidQuery)
SubsquidDatasourceConfigT = TypeVar('SubsquidDatasourceConfigT', bound=SubsquidDatasourceConfig)


def _api_key_headers(api_key: str | None) -> dict[str, str]:
    # NOTE: `v2.archive.subsquid.io` gateways require an API key since 2026-05-19. squid-sdk's
    # NOTE: `ArchiveClient` sends both headers at once, so we mirror it. https://docs.sqd.dev/v2-keys
    if not api_key:
        return {}
    return {'Authorization': f'Bearer {api_key}', 'Token': api_key}


class AbstractSubsquidWorker(Datasource[SubsquidDatasourceConfig], Generic[QueryT]):
    async def run(self) -> None:
        raise FrameworkException('Subsquid worker datasource should not be run')

    async def query(self, query: QueryT) -> list[dict[str, Any]]:
        self._logger.debug('Worker query: %s', query)
        response = await self.request(
            'post',
            url='',
            json=query,
            headers=_api_key_headers(self._config.api_key),
        )
        return cast('list[dict[str, Any]]', response)


class AbstractSubsquidDatasource(
    IndexDatasource[SubsquidDatasourceConfigT],
    Generic[SubsquidDatasourceConfigT, QueryT],
):
    _default_http_config = HttpConfig(
        polling_interval=1.0,
    )

    def __init__(self, config: Any) -> None:
        self._started = asyncio.Event()
        self._last_level: int = 0
        super().__init__(config, False)

    async def run(self) -> None:
        await self._started.wait()

        # NOTE: If node datasource is missing, just poll API in reasonable intervals.
        while True:
            await asyncio.sleep(self._http_config.polling_interval)
            await self.initialize()

    async def start(self) -> None:
        self._started.set()

    async def subscribe(self) -> None:
        pass

    async def initialize(self) -> None:
        curr_level = self._last_level
        level = self._last_level = await self.get_head_level()

        if not level:
            raise DatasourceError('Subsquid is not ready yet', self.name)
        if level == curr_level:
            return

        self.set_sync_level(None, level)
        fire_and_forget(
            Head.update_or_create(
                name=self.name,
                defaults={
                    'level': level,
                    'hash': '',
                    'timestamp': 0,
                },
            ),
        )

    def _api_key_headers(self) -> dict[str, str]:
        return _api_key_headers(self._config.api_key)

    # NOTE: Transport is provided by a mixin (`_ArchiveTransport` / `_PortalTransport`) so the
    # NOTE: chain-specific query/parse logic can be shared across both v2.archive and Portal.
    @abstractmethod
    async def get_head_level(self) -> int: ...

    @abstractmethod
    async def query_worker(self, query: QueryT, current_level: int) -> list[dict[str, Any]]: ...


class _ArchiveTransport(
    AbstractSubsquidDatasource[SubsquidDatasourceConfigT, QueryT],
    Generic[SubsquidDatasourceConfigT, QueryT],
):
    """v2.archive transport: head via `/height`, data via per-level worker indirection."""

    async def get_head_level(self) -> int:
        response = await self.request('get', 'height', headers=self._api_key_headers())
        return int(response)

    # FIXME: Heavily copy-pasted from `HTTPGateway._retry_request`
    async def query_worker(self, query: QueryT, current_level: int) -> list[dict[str, Any]]:
        retry_sleep = self._http_config.retry_sleep
        attempt = 1
        last_attempt = self._http_config.retry_count + 1

        while True:
            try:
                # NOTE: Request a fresh worker after each failed attempt
                worker_datasource = await self._get_worker(current_level)
                async with worker_datasource:
                    return await worker_datasource.query(query)
            except safe_exceptions as e:
                self._logger.warning('Worker query attempt %s/%s failed: %s', attempt, last_attempt, e)
                if attempt == last_attempt:
                    raise e

                self._logger.info('Waiting %s seconds before retry', retry_sleep)
                await asyncio.sleep(retry_sleep)

                attempt += 1
                retry_sleep *= self._http_config.retry_multiplier

    async def _fetch_worker(self, level: int) -> SubsquidDatasourceConfigT:
        worker_url = (
            await self._http.request(
                'get',
                f'{level}/worker',
                headers=self._api_key_headers(),
            )
        ).decode()

        worker_config: SubsquidDatasourceConfigT = copy(self._config)
        worker_config.url = worker_url
        if not worker_config.http:
            worker_config.http = self._default_http_config

        # NOTE: Fail immediately; retries are handled one level up
        worker_config.http.retry_count = 0

        return worker_config

    async def _get_worker(self, level: int) -> AbstractSubsquidWorker[Any]:
        return AbstractSubsquidWorker(await self._fetch_worker(level))


class _PortalTransport(
    AbstractSubsquidDatasource[SubsquidDatasourceConfigT, QueryT],
    Generic[SubsquidDatasourceConfigT, QueryT],
):
    """SQD Portal transport: head via `/finalized-head`, data via NDJSON `/finalized-stream`."""

    # NOTE: Portal requires a `type` field in the query. EVM queries omit it, so the EVM Portal
    # NOTE: datasource sets this hook; chains that already send `type` leave it `None`.
    _portal_dataset_type: str | None = None

    async def get_head_level(self) -> int:
        response = await self.request('get', 'finalized-head', headers=self._api_key_headers())
        return int(response['number'])

    async def query_worker(self, query: QueryT, current_level: int) -> list[dict[str, Any]]:
        body: dict[str, Any] = dict(query)
        if self._portal_dataset_type and 'type' not in body:
            body['type'] = self._portal_dataset_type

        response = await self.request(
            'post',
            'finalized-stream',
            json=body,
            headers=self._api_key_headers(),
        )

        # NOTE: `request()` auto-parses the body with orjson: multi-line NDJSON fails to parse as a
        # NOTE: whole and comes back as raw `bytes` (one block per line); a single line parses to a
        # NOTE: `dict`. An empty stream yields neither.
        if isinstance(response, bytes):
            return [orjson.loads(line) for line in response.splitlines() if line]
        if isinstance(response, dict):
            return [response]
        return []
