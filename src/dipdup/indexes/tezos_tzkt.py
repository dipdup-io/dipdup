from abc import ABC
from typing import Any
from typing import Generic

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
): ...
