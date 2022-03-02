from dipdup.config import CoinbaseDatasourceConfig
from dipdup.config import DipDupConfig
from dipdup.config import HttpDatasourceConfig
from dipdup.config import IpfsDatasourceConfig
from dipdup.config import MetadataDatasourceConfig
from dipdup.config import TzktDatasourceConfig
from dipdup.datasources.coinbase.datasource import CoinbaseDatasource
from dipdup.datasources.const import DatasourceKind
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

        if datasource_config.kind == DatasourceKind.tzkt:
            assert isinstance(datasource_config, TzktDatasourceConfig)
            return cls._build_tzkt_datasource(datasource_config, config)

        if datasource_config.kind == DatasourceKind.coinbase:
            assert isinstance(datasource_config, CoinbaseDatasourceConfig)
            return cls._build_coinbase_datasource(datasource_config)

        if datasource_config.kind == DatasourceKind.metadata:
            assert isinstance(datasource_config, MetadataDatasourceConfig)
            return cls._build_metadata_datasource(datasource_config)

        if datasource_config.kind == DatasourceKind.ipfs:
            assert isinstance(datasource_config, IpfsDatasourceConfig)
            return cls._build_ipfs_datasource(datasource_config)

        if datasource_config.kind == DatasourceKind.http:
            assert isinstance(datasource_config, HttpDatasourceConfig)
            return cls._build_http_datasource(datasource_config)

        raise NotImplementedError

    @classmethod
    def _build_tzkt_datasource(cls, datasource_config: TzktDatasourceConfig, config: DipDupConfig) -> TzktDatasource:
        merge_subscriptions = config.advanced.merge_subscriptions
        return TzktDatasource(
            url=datasource_config.url,
            http_config=datasource_config.http,
            merge_subscriptions=merge_subscriptions,
        )

    @classmethod
    def _build_coinbase_datasource(cls, datasource_config: CoinbaseDatasourceConfig) -> CoinbaseDatasource:
        return CoinbaseDatasource(
            http_config=datasource_config.http,
        )

    @classmethod
    def _build_metadata_datasource(cls, datasource_config: MetadataDatasourceConfig) -> MetadataDatasource:
        return MetadataDatasource(
            url=datasource_config.url,
            network=datasource_config.network,
            http_config=datasource_config.http,
        )

    @classmethod
    def _build_ipfs_datasource(cls, datasource_config: IpfsDatasourceConfig) -> IpfsDatasource:
        return IpfsDatasource(
            url=datasource_config.url,
            http_config=datasource_config.http,
        )

    @classmethod
    def _build_http_datasource(cls, datasource_config: HttpDatasourceConfig) -> HttpDatasource:
        return HttpDatasource(
            http_config=datasource_config.http,
        )
