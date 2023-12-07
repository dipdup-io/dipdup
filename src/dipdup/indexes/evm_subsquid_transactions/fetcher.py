from dipdup.datasources.evm_subsquid import SubsquidDatasource
from dipdup.fetcher import DataFetcher
from dipdup.models.evm_subsquid import SubsquidTransactionData


class TransactionFetcher(DataFetcher[SubsquidTransactionData]):
    _datasource: SubsquidDatasource

    ...
