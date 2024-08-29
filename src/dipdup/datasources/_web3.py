from typing import TYPE_CHECKING
from typing import Any

WEB3_CACHE_SIZE = 256


if TYPE_CHECKING:
    from web3 import AsyncWeb3

    from dipdup.datasources.evm_node import EvmNodeDatasource


async def create_web3_client(datasource: 'EvmNodeDatasource') -> 'AsyncWeb3':
    from web3 import AsyncWeb3
    from web3.providers.async_base import AsyncJSONBaseProvider

    class ProxyProvider(AsyncJSONBaseProvider):
        async def make_request(_, method: str, params: list[Any]) -> Any:
            return await datasource._jsonrpc_request(
                method,
                params,
                raw=True,
                ws=False,
            )

    return AsyncWeb3(
        provider=ProxyProvider(
            cache_allowed_requests=True,
        ),
    )
