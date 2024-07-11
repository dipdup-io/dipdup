from typing import Any

from starknet_py.net.full_node_client import FullNodeClient as OriginalFullNodeClient  # type: ignore[import-untyped]
from starknet_py.net.http_client import HttpMethod  # type: ignore[import-untyped]
from starknet_py.net.http_client import RpcHttpClient as OriginalRpcHttpClient

from dipdup.datasources import Datasource
from dipdup.exceptions import FrameworkException


class RpcHttpClient(OriginalRpcHttpClient):  # type: ignore[misc]
    def __init__(self, datasource: Datasource[Any]) -> None:
        super().__init__(datasource.url)
        self._datasource = datasource

    async def request(
        self,
        address: str,
        http_method: HttpMethod,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | list[dict[str, Any]] | None = None,
    ) -> Any:
        if address != self._datasource.url:
            raise FrameworkException(f'Invalid address: {address} != {self._datasource.url}')
        return await self._datasource.request(
            method=http_method.value,
            url='',
            params=params or {},
            json=payload or {},
        )


class FullNodeClient(OriginalFullNodeClient):  # type: ignore[misc]
    def __init__(
        self,
        datasource: Datasource[Any],
    ):
        self.url = datasource.url
        self._client = RpcHttpClient(datasource)
