from collections.abc import Awaitable
from collections.abc import Callable
from json import JSONDecodeError

import orjson
from aiohttp import web

import dipdup.performance
from dipdup.context import DipDupContext
from dipdup.exceptions import ContractAlreadyExistsError
from dipdup.exceptions import IndexAlreadyExistsError
from dipdup.utils import json_dumps


async def _performance(request: web.Request) -> web.Response:
    return web.json_response(
        dipdup.performance.get_stats(),
        dumps=lambda x: json_dumps(x, option=orjson.OPT_SORT_KEYS).decode(),
    )


def _get_ctx_api_post_method(
    ctx: DipDupContext,
    method: Callable[[DipDupContext, web.Request], Awaitable[web.Response]],
) -> Callable[[web.Request], Awaitable[web.Response]]:
    async def resolved_method(request: web.Request) -> web.Response:
        try:
            return await method(ctx, request)
        except TypeError as e:
            return web.Response(body=f'Bad arguments: {e!r}', status=400)
        except JSONDecodeError:
            return web.Response(body='Request is not a JSON', status=400)

    return resolved_method


async def _add_index(ctx: DipDupContext, request: web.Request) -> web.Response:
    """
    Handle the HTTP API request to add an index.

    HTTP Request:
        - Method: POST
        - URL: /add_index
        - Body: JSON data with parameters
            - name (str): Index name.
            - template (str): Index template to use.
            - values (dict[str, Any]): Mapping of values to fill the template with.
            - first_level (int): First level to start indexing from. Default is 0.
            - last_level (int): Last level to index. Default is 0.
            - state (Index | None): Initial index state (for development only).

    HTTP Response:
        - Status: 200 OK - Index added successfully
        - Status: 400 Bad Request - Index already exists
    """
    try:
        await ctx.add_index(**(await request.json()))
    except IndexAlreadyExistsError:
        return web.Response(body='Index already exists', status=400)
    return web.Response()


async def _add_contract(ctx: DipDupContext, request: web.Request) -> web.Response:
    """
    Handle the HTTP API request to add a contract.

    HTTP Request:
        - Method: POST
        - URL: /add_contract
        - Body: JSON data with parameters
            - kind (Literal['tezos'] | Literal['evm']): Blockchain kind. Either 'tezos' or 'evm' allowed.
            - name (str): Contract name.
            - address (str | None): Contract address. Optional, default is None.
            - typename (str | None): Alias for the contract script. Optional, default is None.
            - code_hash (str | int | None): Contract code hash. Optional, default is None.

    HTTP Response:
        - Status: 200 OK - Contract added successfully
        - Status: 400 Bad Request - Contract already exists or invalid parameters
    """
    try:
        await ctx.add_contract(**(await request.json()))
    except ContractAlreadyExistsError:
        return web.Response(body='Contract already exists', status=400)
    return web.Response()


async def create_api(ctx: DipDupContext) -> web.Application:
    routes = web.RouteTableDef()
    routes.get('/performance')(_performance)
    routes.post('/add_index')(_get_ctx_api_post_method(ctx, _add_index))
    routes.post('/add_contract')(_get_ctx_api_post_method(ctx, _add_contract))

    app = web.Application()
    app.add_routes(routes)
    return app
