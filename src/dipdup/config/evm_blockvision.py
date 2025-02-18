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
class EvmBlockvisionDatasourceConfig(DatasourceConfig):
    """Blockvision datasource config

    :param kind: always 'evm.blockvision'
    :param url: API URL
    :param api_key: API key
    :param http: HTTP client configuration
    """

    kind: Literal['evm.blockvision'] = 'evm.blockvision'
    url: Url
    api_key: str | None = None

    http: HttpConfig | None = None
