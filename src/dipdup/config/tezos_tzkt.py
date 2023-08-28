from typing import Literal
from urllib.parse import urlparse

from pydantic.dataclasses import dataclass

from dipdup.config import HttpConfig
from dipdup.config import IndexConfig
from dipdup.config import IndexDatasourceConfig
from dipdup.exceptions import ConfigurationError
from dipdup.models.tezos_tzkt import HeadSubscription
from dipdup.subscriptions import Subscription

TZKT_API_URLS: dict[str, str] = {
    'https://api.tzkt.io': 'mainnet',
    'https://api.ghostnet.tzkt.io': 'ghostnet',
    'https://api.limanet.tzkt.io': 'limanet',
    'https://staging.api.tzkt.io': 'staging',
}


DEFAULT_TZKT_URL = next(iter(TZKT_API_URLS.keys()))
MAX_BATCH_SIZE = 10000


@dataclass
class TzktDatasourceConfig(IndexDatasourceConfig):
    """TzKT datasource config

    :param kind: always 'tezos.tzkt'
    :param url: Base API URL, e.g. https://api.tzkt.io/
    :param http: HTTP client configuration
    :param buffer_size: Number of levels to keep in FIFO buffer before processing
    :param merge_subscriptions: Whether to merge realtime subscriptions
    :param rollback_depth: Number of blocks to keep in the database to handle reorgs
    """

    kind: Literal['tezos.tzkt']
    url: str = DEFAULT_TZKT_URL
    http: HttpConfig | None = None
    buffer_size: int = 0
    merge_subscriptions: bool = False
    rollback_depth: int = 2

    def __post_init_post_parse__(self) -> None:
        super().__post_init_post_parse__()
        self.url = self.url.rstrip('/')

        limit = MAX_BATCH_SIZE
        if self.http and self.http.batch_size and self.http.batch_size > limit:
            raise ConfigurationError(f'`batch_size` must be less than {limit}')
        # NOTE: It's a `config export` call with environment variable substitution disabled
        if '$' in self.url:
            return
        parsed_url = urlparse(self.url)
        if not (parsed_url.scheme and parsed_url.netloc):
            raise ConfigurationError(f'`{self.url}` is not a valid TzKT API URL')


@dataclass
class TzktIndexConfig(IndexConfig):
    datasource: TzktDatasourceConfig

    def get_subscriptions(self) -> set[Subscription]:
        return {HeadSubscription()}
