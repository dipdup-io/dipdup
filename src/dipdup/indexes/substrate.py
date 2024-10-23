from abc import ABC
from typing import TYPE_CHECKING
from typing import Generic
from typing import TypeVar

from dipdup.config import SubstrateIndexConfigU
from dipdup.datasources.substrate_node import SubstrateNodeDatasource
from dipdup.datasources.substrate_subscan import SubstrateSubscanDatasource
from dipdup.datasources.substrate_subsquid import SubstrateSubsquidDatasource
from dipdup.index import IndexQueueItemT
from dipdup.indexes.evm import EvmIndex
from dipdup.runtimes import SubstrateRuntime

SubstrateDatasource = SubstrateSubsquidDatasource | SubstrateSubscanDatasource | SubstrateNodeDatasource

IndexConfigT = TypeVar('IndexConfigT', bound=SubstrateIndexConfigU)
DatasourceT = TypeVar('DatasourceT', bound=SubstrateDatasource)

if TYPE_CHECKING:
    from dipdup.context import DipDupContext


class SubstrateIndex(
    Generic[IndexConfigT, IndexQueueItemT, DatasourceT],
    # FIXME: it's not
    EvmIndex[IndexConfigT, IndexQueueItemT, DatasourceT],
    ABC,
):
    def __init__(
        self,
        ctx: 'DipDupContext',
        config: IndexConfigT,
        datasources: tuple[DatasourceT, ...],
    ) -> None:
        super().__init__(ctx, config, datasources)
        self.runtime = SubstrateRuntime(
            config=config.runtime,
            package=ctx.package,
        )
