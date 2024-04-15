from dipdup.datasources.evm_subsquid import EvmSubsquidDatasource
from dipdup.fetcher import DataFetcher
from dipdup.models.evm_subsquid import EvmSubsquidTraceData


class EvmSubsquidTraceFetcher(DataFetcher[EvmSubsquidTraceData]):
    _datasource: EvmSubsquidDatasource

    ...
