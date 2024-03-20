from abc import ABC
from typing import Any
from typing import Generic

from dipdup.datasources.tezos_tzkt import TzktDatasource
from dipdup.index import Index
from dipdup.index import IndexConfigT
from dipdup.index import IndexQueueItemT
from dipdup.models.tezos_tzkt import TzktMessageType

TZKT_READAHEAD_LIMIT = 10000


class TzktIndex(
    Generic[IndexConfigT, IndexQueueItemT],
    Index[Any, Any, TzktDatasource],
    ABC,
    message_type=TzktMessageType,  # type: ignore[arg-type]
): ...
