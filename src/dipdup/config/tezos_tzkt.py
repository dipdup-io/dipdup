from typing import Literal
from urllib.parse import urlparse

from pydantic.dataclasses import dataclass

from dipdup import baking_bad
from dipdup.config import DEFAULT_TZKT_URL
from dipdup.config import HttpConfig
from dipdup.config import IndexConfig
from dipdup.config import IndexDatasourceConfig
from dipdup.exceptions import ConfigurationError


@dataclass
class TzktDatasourceConfig(IndexDatasourceConfig):
    """TzKT datasource config

    :param kind: always 'tezos.tzkt'
    :param url: Base API URL, e.g. https://api.tzkt.io/
    :param http: HTTP client configuration
    :param buffer_size: Number of levels to keep in FIFO buffer before processing
    """

    kind: Literal['tezos.tzkt']
    url: str = DEFAULT_TZKT_URL  # type: ignore
    http: HttpConfig | None = None
    buffer_size: int = 0
    merge_subscriptions: bool = False

    def __post_init_post_parse__(self) -> None:
        super().__post_init_post_parse__()
        self.url = self.url.rstrip('/')

        # NOTE: Is is possible to increase limits in TzKT? Anyway, I don't think anyone will ever need it.
        limit = baking_bad.MAX_TZKT_BATCH_SIZE
        if self.http and self.http.batch_size and self.http.batch_size > limit:
            raise ConfigurationError(f'`batch_size` must be less than {limit}')
        parsed_url = urlparse(self.url)
        # NOTE: Environment substitution disabled
        if '$' in self.url:
            return
        if not (parsed_url.scheme and parsed_url.netloc):
            raise ConfigurationError(f'`{self.url}` is not a valid datasource URL')


@dataclass
class TzktIndexConfig(IndexConfig):
    datasource: TzktDatasourceConfig
