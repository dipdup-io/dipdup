from dipdup.config import DipDupConfig
from dipdup.config.coinbase import CoinbaseDatasourceConfig
from dipdup.config.evm_subsquid import SubsquidDatasourceConfig
from dipdup.config.http import HttpDatasourceConfig
from dipdup.config.ipfs import IpfsDatasourceConfig
from dipdup.config.tezos_tzkt import TzktDatasourceConfig
from dipdup.config.tzip_metadata import TzipMetadataDatasourceConfig
from dipdup.datasources import Datasource
from dipdup.datasources.coinbase import CoinbaseDatasource
from dipdup.datasources.evm_subsquid import EvmSubsquidDatasource
from dipdup.datasources.http import HttpDatasource
from dipdup.datasources.ipfs import IpfsDatasource
from dipdup.datasources.metadata import TzipMetadataDatasource
from dipdup.datasources.tezos_tzkt import TzktDatasource


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

        if isinstance(datasource_config, TzipMetadataDatasourceConfig):
            return TzipMetadataDatasource(
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

        if isinstance(datasource_config, SubsquidDatasourceConfig):
            return EvmSubsquidDatasource(
                archive_url=datasource_config.archive_url,
                node_url=datasource_config.node_url,
                http_config=datasource_config.http,
            )

        raise NotImplementedError
