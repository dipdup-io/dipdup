from __future__ import annotations

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from dipdup.config import DatasourceConfig


@dataclass(config=ConfigDict(extra='forbid', defer_build=True), kw_only=True)
class SubsquidDatasourceConfig(DatasourceConfig):
    """Base class for Subsquid datasource configs

    :param api_key: API key
    """

    api_key: str | None = None

    @property
    def merge_subscriptions(self) -> bool:
        return False

    @property
    def rollback_depth(self) -> int:
        # NOTE: Subsquid data is always finalized
        return 0
