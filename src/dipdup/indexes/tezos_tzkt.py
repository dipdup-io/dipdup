from abc import ABC
from typing import Any
from typing import Generic

from dipdup.context import DipDupContext
from dipdup.datasources.tezos_tzkt import TezosTzktDatasource
from dipdup.index import Index
from dipdup.index import IndexConfigT
from dipdup.index import IndexQueueItemT
from dipdup.models.tezos_tzkt import TezosTzktMessageType

TZKT_READAHEAD_LIMIT = 10000


class TezosTzktIndex(
    Generic[IndexConfigT, IndexQueueItemT],
    Index[Any, Any, TezosTzktDatasource],
    ABC,
    message_type=TezosTzktMessageType,  # type: ignore[arg-type]
):
    def __init__(
        self,
        ctx: DipDupContext,
        config: Any,
        datasource: TezosTzktDatasource,
    ) -> None:
        self._datasource = datasource
        super().__init__(ctx, config, (datasource,))

    @property
    def datasource(self) -> TezosTzktDatasource:
        return self._datasource
