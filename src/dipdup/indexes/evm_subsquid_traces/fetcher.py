from dipdup.datasources.evm_subsquid import SubsquidDatasource
from dipdup.fetcher import DataFetcher
from dipdup.models.evm_subsquid import SubsquidTraceData


class TraceFetcher(DataFetcher[SubsquidTraceData]):
    _datasource: SubsquidDatasource

    ...
