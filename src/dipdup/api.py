import functools
from collections.abc import Awaitable
from collections.abc import Callable
from json import JSONDecodeError

import orjson
from aiohttp import web

import dipdup.performance
from dipdup.context import DipDupContext
from dipdup.exceptions import Error
from dipdup.utils import json_dumps


def _method_wrapper(
    ctx: DipDupContext,
    method: Callable[[DipDupContext, web.Request], Awaitable[web.Response]],
) -> Callable[[web.Request], Awaitable[web.Response]]:
    @functools.wraps(method)
    async def resolved_method(request: web.Request) -> web.Response:
        try:
            return await method(ctx, request)
        except TypeError as e:
            return web.Response(body=f'Invalid parameters: {e.args[0]}', status=400)
        except JSONDecodeError:
            return web.Response(body='Request is not a JSON', status=400)
        except Error as e:
            return web.Response(body=str(e), status=400)
        except Exception as e:
            return web.Response(body=str(e), status=500)

    return resolved_method


async def _add_index(ctx: DipDupContext, request: web.Request) -> web.Response:
    await ctx.add_index(**(await request.json()))
    return web.Response()


async def _add_contract(ctx: DipDupContext, request: web.Request) -> web.Response:
    await ctx.add_contract(**(await request.json()))
    return web.Response()


async def _performance(ctx: DipDupContext, request: web.Request) -> web.Response:
    return web.json_response(
        dipdup.performance.get_stats(),
        dumps=lambda x: json_dumps(x, option=orjson.OPT_SORT_KEYS).decode(),
    )


async def create_api(ctx: DipDupContext) -> web.Application:
    routes = web.RouteTableDef()
    routes.get('/performance')(_method_wrapper(ctx, _performance))
    routes.post('/add_index')(_method_wrapper(ctx, _add_index))
    routes.post('/add_contract')(_method_wrapper(ctx, _add_contract))

    app = web.Application()
    app.add_routes(routes)
    return app
