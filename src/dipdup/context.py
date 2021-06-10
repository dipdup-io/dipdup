from abc import abstractmethod
from collections import deque, namedtuple
from contextlib import suppress
import logging
from typing import Any, Deque, Dict, List, Optional, Set, Tuple, Union, cast

from pydantic import BaseModel
from dipdup.config import (
    BigMapHandlerConfig,
    BigMapHandlerPatternConfig,
    BigMapIndexConfig,
    ContractConfig,
    DipDupConfig,
    IndexConfig,
    IndexConfigT,
    IndexConfigTemplateT,
    OperationHandlerConfig,
    OperationHandlerOriginationPatternConfig,
    OperationHandlerPatternConfigT,
    OperationHandlerTransactionPatternConfig,
    OperationIndexConfig,
    OperationType,
)
from dipdup.datasources import DatasourceT
from dipdup.datasources.tzkt.datasource import BigMapFetcher, OperationFetcher, TzktDatasource
from dipdup.models import (
    BigMapAction,
    BigMapDiff,
    BigMapData,
    OperationData,
    Origination,
    State,
    TemporaryState,
    Transaction,
)
from tortoise.transactions import in_transaction

from dipdup.utils import reindex, restart
from pydantic.dataclasses import dataclass


class HandlerContext:
    """Common handler context."""

    def __init__(
        self,
        datasources: Dict[str, DatasourceT],
        config: DipDupConfig,
    ) -> None:
        self.datasources = datasources
        self.config = config
        self._updated: bool = False

    def commit(self) -> None:
        """Spawn indexes after handler execution"""
        self._updated = True

    def reset(self) -> None:
        self._updated = False

    @property
    def updated(self) -> bool:
        return self._updated

    async def reindex(self) -> None:
        await reindex()

    async def restart(self) -> None:
        await restart()

    # TODO
    async def add_contract(self):
        ...

    # TODO
    async def add_index(self):
        ...


class OperationHandlerContext(HandlerContext):
    """Operation index handler context (first argument)"""

    def __init__(
        self,
        datasources: Dict[str, DatasourceT],
        config: DipDupConfig,
        operations: List[OperationData],
        template_values: Optional[Dict[str, str]],
    ) -> None:
        super().__init__(datasources, config)
        self.operations = operations
        self.template_values = template_values


class BigMapHandlerContext(HandlerContext):
    """Big map index handler context (first argument)"""

    def __init__(
        self,
        datasources: Dict[str, DatasourceT],
        config: DipDupConfig,
        template_values: Optional[Dict[str, str]],
    ) -> None:
        super().__init__(datasources, config)
        self.template_values = template_values
