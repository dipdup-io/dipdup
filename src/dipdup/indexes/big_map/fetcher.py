from __future__ import annotations

import logging
from typing import AsyncGenerator
from typing import Iterable

from dipdup.config import BigMapHandlerConfig
from dipdup.config import BigMapIndexConfig
from dipdup.datasources.tzkt.datasource import TzktDatasource
from dipdup.fetcher import DataFetcher
from dipdup.fetcher import yield_by_level
from dipdup.models import BigMapData


def get_big_map_addresses(handlers: Iterable[BigMapHandlerConfig]) -> set[str]:
    """Get addresses to fetch big map diffs from during initial synchronization"""
    addresses = set()
    for handler_config in handlers:
        addresses.add(handler_config.contract.get_address())
    return addresses


def get_big_map_paths(handlers: Iterable[BigMapHandlerConfig]) -> set[str]:
    """Get addresses to fetch big map diffs from during initial synchronization"""
    paths = set()
    for handler_config in handlers:
        paths.add(handler_config.path)
    return paths


def get_big_map_pairs(handlers: Iterable[BigMapHandlerConfig]) -> set[tuple[str, str]]:
    """Get address-path pairs for fetch big map diffs during sync with `skip_history`"""
    pairs = set()
    for handler_config in handlers:
        pairs.add(
            (
                handler_config.contract.get_address(),
                handler_config.path,
            )
        )
    return pairs


class BigMapFetcher(DataFetcher[BigMapData]):
    """Fetches bigmap diffs from REST API, merges them and yields by level."""

    def __init__(
        self,
        datasource: 'TzktDatasource',
        first_level: int,
        last_level: int,
        big_map_addresses: set[str],
        big_map_paths: set[str],
    ) -> None:
        super().__init__(datasource, first_level, last_level)
        self._logger = logging.getLogger('dipdup.tzkt')
        self._big_map_addresses = big_map_addresses
        self._big_map_paths = big_map_paths

    @classmethod
    def create(
        cls,
        config: BigMapIndexConfig,
        datasource: TzktDatasource,
        first_level: int,
        last_level: int,
    ) -> BigMapFetcher:
        big_map_addresses = get_big_map_addresses(config.handlers)
        big_map_paths = get_big_map_paths(config.handlers)

        return BigMapFetcher(
            datasource=datasource,
            first_level=first_level,
            last_level=last_level,
            big_map_addresses=big_map_addresses,
            big_map_paths=big_map_paths,
        )

    async def fetch_by_level(self) -> AsyncGenerator[tuple[int, tuple[BigMapData, ...]], None]:
        """Iterate over big map diffs fetched fetched from REST.

        Resulting data is splitted by level, deduped, sorted and ready to be processed by BigMapIndex.
        """
        big_map_iter = self._datasource.iter_big_maps(
            self._big_map_addresses,
            self._big_map_paths,
            self._first_level,
            self._last_level,
        )
        async for level, batch in yield_by_level(big_map_iter):
            yield level, batch
