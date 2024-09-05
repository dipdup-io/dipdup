from __future__ import annotations

from typing import TYPE_CHECKING

from dipdup.config.tezos_big_maps import TezosBigMapsHandlerConfig
from dipdup.indexes.tezos_tzkt import TezosTzktFetcher
from dipdup.models.tezos import TezosBigMapData

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator
    from collections.abc import Iterable

    from dipdup.config.tezos_big_maps import TezosBigMapsIndexConfig
    from dipdup.datasources.tezos_tzkt import TezosTzktDatasource


def get_big_map_addresses(handlers: Iterable[TezosBigMapsHandlerConfig]) -> set[str]:
    """Get addresses to fetch big map diffs from during initial synchronization"""
    addresses = set()
    for handler_config in handlers:
        addresses.add(handler_config.contract.get_address())
    return addresses


def get_big_map_paths(handlers: Iterable[TezosBigMapsHandlerConfig]) -> set[str]:
    """Get addresses to fetch big map diffs from during initial synchronization"""
    paths = set()
    for handler_config in handlers:
        paths.add(handler_config.path)
    return paths


def get_big_map_pairs(handlers: Iterable[TezosBigMapsHandlerConfig]) -> list[tuple[str, str]]:
    """Get address-path pairs for fetch big map diffs during sync with `skip_history`"""
    pairs = []
    for handler_config in handlers:
        pairs.append(
            (
                handler_config.contract.get_address(),
                handler_config.path,
            )
        )
    return pairs


class BigMapFetcher(TezosTzktFetcher[TezosBigMapData]):
    """Fetches bigmap diffs from REST API, merges them and yields by level."""

    def __init__(
        self,
        name: str,
        datasources: tuple[TezosTzktDatasource, ...],
        first_level: int,
        last_level: int,
        big_map_addresses: set[str],
        big_map_paths: set[str],
    ) -> None:
        super().__init__(
            name=name,
            datasources=datasources,
            first_level=first_level,
            last_level=last_level,
        )
        self._big_map_addresses = big_map_addresses
        self._big_map_paths = big_map_paths

    @classmethod
    def create(
        cls,
        config: TezosBigMapsIndexConfig,
        datasources: tuple[TezosTzktDatasource, ...],
        first_level: int,
        last_level: int,
    ) -> BigMapFetcher:
        big_map_addresses = get_big_map_addresses(config.handlers)
        big_map_paths = get_big_map_paths(config.handlers)

        return BigMapFetcher(
            name=config.name,
            datasources=datasources,
            first_level=first_level,
            last_level=last_level,
            big_map_addresses=big_map_addresses,
            big_map_paths=big_map_paths,
        )

    async def fetch_by_level(self) -> AsyncGenerator[tuple[int, tuple[TezosBigMapData, ...]], None]:
        big_map_iter = self.random_datasource.iter_big_maps(
            self._big_map_addresses,
            self._big_map_paths,
            self._first_level,
            self._last_level,
        )
        async for level, batch in self.readahead_by_level(big_map_iter):
            yield level, batch
