from dipdup.config import HttpConfig
from dipdup.datasources import IndexDatasource


class EvmSubsquidDatasource(IndexDatasource):
    _default_http_config = HttpConfig()

    def __init__(
        self,
        archive_url: str,
        node_url: str | None = None,
        http_config: HttpConfig | None = None,
    ) -> None:
        super().__init__(archive_url, http_config)
        self.archive_url = archive_url
        self.node_url = node_url

    async def run(self) -> None:
        pass

    async def subscribe(self) -> None:
        raise NotImplementedError
