from dipdup.config import CoinbaseDatasourceConfig
from dipdup.config import DipDupConfig
from dipdup.config import HttpDatasourceConfig
from dipdup.config import IpfsDatasourceConfig
from dipdup.config import MetadataDatasourceConfig
from dipdup.config import TzktDatasourceConfig
from dipdup.datasources.coinbase.datasource import CoinbaseDatasource
from dipdup.datasources.datasource import Datasource
from dipdup.datasources.datasource import HttpDatasource
from dipdup.datasources.ipfs.datasource import IpfsDatasource
from dipdup.datasources.metadata.datasource import MetadataDatasource
from dipdup.datasources.tzkt.datasource import TzktDatasource


class DatasourceFactory:
    """Decouple Context logic and knowledge about Datasources implementation and creation"""

    @classmethod
    def build(cls, name: str, config: DipDupConfig) -> Datasource:
        datasource = cls._build_datasource(name, config)
        datasource.set_logger(name)
        datasource.set_user_agent(config.package)

        return datasource

    @classmethod
    def _build_datasource(cls, name: str, config: DipDupConfig) -> Datasource:
        datasource_config = config.get_datasource(name)

        if isinstance(datasource_config, TzktDatasourceConfig):
            return TzktDatasource(
                url=datasource_config.url,
                http_config=datasource_config.http,
                merge_subscriptions=config.advanced.merge_subscriptions,
                buffer_size=datasource_config.buffer_size,
            )

        if isinstance(datasource_config, CoinbaseDatasourceConfig):
            return CoinbaseDatasource(
                http_config=datasource_config.http,
            )

        if isinstance(datasource_config, MetadataDatasourceConfig):
            return MetadataDatasource(
                url=datasource_config.url,
                network=datasource_config.network,
                http_config=datasource_config.http,
            )

        if isinstance(datasource_config, IpfsDatasourceConfig):
            return IpfsDatasource(
                url=datasource_config.url,
                http_config=datasource_config.http,
            )

        if isinstance(datasource_config, HttpDatasourceConfig):
            return HttpDatasource(
                url=datasource_config.url,
                http_config=datasource_config.http,
            )

        raise NotImplementedError
