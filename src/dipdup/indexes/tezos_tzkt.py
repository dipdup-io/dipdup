from abc import ABC
from typing import TYPE_CHECKING
from typing import Any
from typing import Generic

from dipdup.datasources.tezos_tzkt import TezosTzktDatasource
from dipdup.index import Index
from dipdup.index import IndexConfigT
from dipdup.index import IndexQueueItemT
from dipdup.models.tezos_tzkt import TezosTzktMessageType

if TYPE_CHECKING:
    from dipdup.context import DipDupContext


TZKT_READAHEAD_LIMIT = 10000


class TezosIndex(
    Generic[IndexConfigT, IndexQueueItemT],
    Index[Any, Any, TezosTzktDatasource],
    ABC,
    message_type=TezosTzktMessageType,  # type: ignore[arg-type]
):
    def __init__(
        self,
        ctx: 'DipDupContext',
        config: Any,
        datasource: TezosTzktDatasource,
    ) -> None:
        self._datasource = datasource
        super().__init__(ctx, config, (datasource,))

    @property
    def datasource(self) -> TezosTzktDatasource:
        return self._datasource
