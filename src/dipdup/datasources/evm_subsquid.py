from dipdup.config import HttpConfig
from dipdup.config.evm_subsquid import SubsquidDatasourceConfig
from dipdup.datasources import IndexDatasource


class SubsquidDatasource(IndexDatasource[SubsquidDatasourceConfig]):
    _default_http_config = HttpConfig()

    async def run(self) -> None:
        pass

    async def subscribe(self) -> None:
        raise NotImplementedError
