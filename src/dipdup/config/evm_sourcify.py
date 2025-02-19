from __future__ import annotations

import logging
from typing import Literal

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from dipdup.config import DatasourceConfig
from dipdup.config import HttpConfig
from dipdup.config import Url

_logger = logging.getLogger(__name__)


@dataclass(config=ConfigDict(extra='forbid', defer_build=True), kw_only=True)
class EvmSourcifyDatasourceConfig(DatasourceConfig):
    """Sourcify datasource config

    :param kind: always 'evm.sourcify'
    :param url: API URL
    :param chain_id: Chain ID
    :param api_key: API key
    :param http: HTTP client configuration
    """

    kind: Literal['evm.sourcify'] = 'evm.sourcify'
    url: Url = 'https://sourcify.dev/server'
    chain_id: int
    api_key: str | None = None

    http: HttpConfig | None = None
