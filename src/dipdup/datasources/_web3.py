from typing import TYPE_CHECKING
from typing import Any

WEB3_CACHE_SIZE = 256


if TYPE_CHECKING:
    from web3 import AsyncWeb3

    from dipdup.datasources.evm_node import EvmNodeDatasource


async def create_web3_client(datasource: 'EvmNodeDatasource') -> 'AsyncWeb3':
    from web3 import AsyncWeb3
    from web3.middleware.async_cache import async_construct_simple_cache_middleware
    from web3.providers.async_base import AsyncJSONBaseProvider
    from web3.utils.caching import SimpleCache

    from dipdup.performance import caches

    web3_cache = SimpleCache(WEB3_CACHE_SIZE)
    caches.add_plain(web3_cache._data, f'{datasource.name}:web3_cache')

    class ProxyProvider(AsyncJSONBaseProvider):
        async def make_request(_, method: str, params: list[Any]) -> Any:
            return await datasource._jsonrpc_request(
                method,
                params,
                raw=True,
                ws=False,
            )

    web3_client = AsyncWeb3(
        provider=ProxyProvider(),
    )
    web3_client.middleware_onion.add(
        await async_construct_simple_cache_middleware(web3_cache),
        'cache',
    )
    return web3_client
