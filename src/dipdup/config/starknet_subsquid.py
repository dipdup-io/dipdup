from typing import Literal

from pydantic import ConfigDict
from pydantic import field_validator
from pydantic.dataclasses import dataclass

from dipdup.config import HttpConfig
from dipdup.config import IndexDatasourceConfig
from dipdup.exceptions import ConfigurationError


@dataclass(config=ConfigDict(extra='forbid'), kw_only=True)
class StarknetSubsquidDatasourceConfig(IndexDatasourceConfig):
    """Subsquid datasource config

    :param kind: always 'starknet.subsquid'
    :param url: URL of Subsquid Network API
    :param http: HTTP client configuration
    """

    kind: Literal['starknet.subsquid']
    url: str
    http: HttpConfig | None = None

    @property
    def merge_subscriptions(self) -> bool:
        return False

    @property
    def rollback_depth(self) -> int:
        return 0

    @field_validator('url')
    @classmethod
    def _valid_url(cls, v: str) -> str:
        if not v.startswith(('http', 'https')):
            raise ConfigurationError('Subsquid Network URL must start with http(s)')
        return v
